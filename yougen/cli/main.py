"""CLI命令入口"""

import asyncio
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime
import argparse

from yougen.core.bird_client import BirdClient, BirdClientError
from yougen.core.browser_client import BrowserClient
from yougen.core.tweet_collector import TweetCollector
from yougen.core.trend_analyzer import TrendAnalyzer
from yougen.core.comment_generator import CommentGenerator
from yougen.core.quality_filter import TweetQualityFilter
from yougen.storage.file_store import FileStore
from yougen.storage.models import Influencer
from yougen.cli.reviewer import run_review
from yougen.config import load_settings, get_quality_filter_config


class YouGen:
    """YouGen CLI主程序"""

    def __init__(self, config_dir: Optional[Path] = None, data_dir: Optional[Path] = None, debug: bool = False, use_cdp: bool = True):
        # 默认路径
        self.config_dir = config_dir or Path.cwd() / "yougen" / "config"
        self.data_dir = data_dir or Path.cwd() / "yougen" / "data"
        self.debug = debug
        self.use_cdp = use_cdp

        # 加载配置
        self.user_profile = self._load_yaml(self.config_dir / "user_profile.yaml")
        self.settings = self._load_yaml(self.config_dir / "settings.yaml")

        # 初始化组件
        self.store = FileStore(self.data_dir)
        self._init_influencers_from_config()  # 从配置初始化influencers
        self.bird = BirdClient(delay=self.settings['rate_limit']['delay_seconds'])
        self.browser = BrowserClient(
            delay=self.settings['rate_limit']['delay_seconds'],
            session_name="",  # 使用默认 session
            headed=debug,  # Debug 模式下显示浏览器（非CDP模式）
            use_cdp=use_cdp,  # 默认使用 CDP 模式连接真实 Chrome
            cdp_port=9222  # CDP 端口
        )

        # 创建质量过滤器
        filter_config = get_quality_filter_config(self.settings)
        quality_filter = TweetQualityFilter(filter_config) if filter_config.get('enabled') else None

        self.collector = TweetCollector(self.bird, self.store, quality_filter)
        self.analyzer = TrendAnalyzer(
            like_weight=self.settings['trend_analysis']['like_weight'],
            retweet_weight=self.settings['trend_analysis']['retweet_weight'],
            reply_weight=self.settings['trend_analysis']['reply_weight']
        )
        self.generator = CommentGenerator(self.user_profile)

    def _load_yaml(self, path: Path) -> dict:
        """加载YAML配置"""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _init_influencers_from_config(self):
        """从配置文件初始化influencers到数据存储"""
        config_file = self.config_dir / "influencers.yaml"

        # 如果配置文件不存在，跳过
        if not config_file.exists():
            return

        managed_file = self.data_dir / "influencers" / "managed.json"

        # 检查是否需要重新加载
        should_reload = False

        if not managed_file.exists():
            # managed.json不存在，需要加载
            should_reload = True
        else:
            # 比较修改时间，如果YAML比managed.json新，重新加载
            config_mtime = config_file.stat().st_mtime
            managed_mtime = managed_file.stat().st_mtime

            if config_mtime > managed_mtime:
                print(f"⚠️  influencers.yaml has been modified, reloading...")
                should_reload = True

        if not should_reload:
            return

        # 从YAML加载配置
        config = self._load_yaml(config_file)
        influencers_data = config.get('influencers', [])

        if not influencers_data:
            return

        # 转换为Influencer对象
        influencers = []
        for item in influencers_data:
            influencer = Influencer(
                username=item['username'],
                user_id=item.get('user_id', ''),
                priority=item.get('priority', 'medium'),
                check_interval=item.get('check_interval', 15),
                topics=item.get('topics', []),
                notes=item.get('notes', ''),
                added_at=datetime.now()
            )
            influencers.append(influencer)

        # 保存到managed.json
        self.store.save_influencers(influencers)
        print(f"✅ Loaded {len(influencers)} influencer(s) from config")

    def check_auth(self):
        """检查bird CLI认证状态"""
        print("🔐 Checking bird CLI authentication...")
        success, result = self.bird.check_auth()

        if success:
            print(f"✅ Authenticated as @{result}")
            return True
        else:
            print(f"❌ Authentication failed: {result}")
            print("\nPlease authenticate with: bird login")
            return False

    async def scan_and_generate(self):
        """扫描推文并生成评论"""
        print("\n🚀 Starting tweet scan and comment generation...")
        print("=" * 80)

        # 1. 加载大V列表
        influencers = self.store.load_influencers()
        if not influencers:
            print("⚠️  No influencers configured")
            print(f"Please add influencers to: {self.config_dir / 'influencers.yaml'}")
            return

        print(f"📋 Loaded {len(influencers)} influencer(s)")

        # 2. 收集推文
        print("\n📡 Collecting tweets...")
        max_age = self.settings['collection']['max_tweet_age_minutes']
        tweets = self.collector.collect_from_influencers(influencers, max_age_minutes=max_age)

        if not tweets:
            print("📭 No new tweets found")
            return

        print(f"✅ Collected {len(tweets)} new tweet(s)")

        # 3. 趋势分析
        print("\n📈 Analyzing trends...")
        min_score = self.settings['trend_analysis']['min_score']
        max_tweets = self.settings['collection']['max_tweets_per_scan']

        ranked = self.analyzer.rank_tweets(
            tweets,
            min_score=min_score,
            min_tweets=3
        )

        # 限制数量
        ranked = ranked[:max_tweets]

        print(f"🎯 Selected {len(ranked)} trending tweet(s)")
        for i, tweet in enumerate(ranked, 1):
            print(f"   {i}. @{tweet.author.username}: {tweet.trending_score}/100")

        # 4. 生成评论
        print("\n🤖 Generating comments...")
        comments = await self.generator.generate_batch(
            ranked,
            max_concurrent=self.settings['rate_limit']['max_concurrent_generations']
        )

        # 5. 保存评论
        for comment in comments:
            self.store.save_comment(comment)

        print(f"\n✅ Generated {len(comments)} comment(s)")
        print("=" * 80)

        # 6. 显示统计
        stats = self.store.get_comment_stats()
        print("\n📊 Comment Stats:")
        print(f"   Pending: {stats['pending']}")
        print(f"   Approved: {stats['approved']}")
        print(f"   Published: {stats['published']}")
        print(f"   Rejected: {stats['rejected']}")

    def review_comments(self, use_browser: bool = True):
        """
        审核评论

        Args:
            use_browser: 是否使用浏览器模式发布
        """
        print("\n📝 Starting comment review...")
        run_review(self.store, self.bird, self.browser, self.generator, use_browser)

    def publish_approved(self, use_browser: bool = True):
        """
        发布已批准的评论

        Args:
            use_browser: 是否使用浏览器模式（agent-browser），默认True
        """
        print("\n🚀 Publishing approved comments...")

        # 如果使用浏览器模式，先检查登录状态
        if use_browser:
            if not self.browser.ensure_logged_in():
                print("❌ Please login to Twitter first")
                return

        approved = self.store.load_comments_by_status('approved')

        if not approved:
            print("📭 No approved comments to publish")
            return

        print(f"Found {len(approved)} approved comment(s)")

        success_count = 0
        for i, comment in enumerate(approved, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{len(approved)}] Comment ID: {comment.id[:8]}")

            # 获取推文信息
            tweet = self.bird.get_tweet_by_id(comment.tweet_id)
            if not tweet:
                print(f"   ⚠️  Could not find tweet {comment.tweet_id}, skipping")
                continue

            # 显示推文和评论内容
            print(f"\n📝 Tweet by @{tweet.author.username}:")
            print(f"   {tweet.text[:100]}{'...' if len(tweet.text) > 100 else ''}")
            print(f"\n💬 Comment to publish:")
            print(f"   \"{comment.content}\"")
            print(f"\n🔗 Tweet URL: https://twitter.com/{tweet.author.username}/status/{comment.tweet_id}")

            # 人工确认
            current_content = comment.content
            while True:
                print(f"\n💬 Current comment: \"{current_content}\"")
                confirm = input("\n❓ [y]es / [e]dit / [s]kip / [q]uit: ").lower().strip()

                if confirm == 'y' or confirm == 'yes':
                    print(f"\n📤 Publishing...")
                    tweet_url = f"https://twitter.com/{tweet.author.username}/status/{comment.tweet_id}"

                    # 使用浏览器或bird CLI发布
                    if use_browser:
                        success = self.browser.post_reply(tweet_url, current_content)
                    else:
                        success = self.bird.post_reply(comment.tweet_id, current_content)

                    if success:
                        # 如果内容被修改了，更新到数据库
                        if current_content != comment.content:
                            comment.content = current_content
                            self.store.save_comment(comment)
                        self.store.update_comment_status(comment.id, 'published')
                        success_count += 1
                        print("   ✅ Published successfully!")
                    else:
                        print("   ❌ Failed to publish")
                    break

                elif confirm == 'e' or confirm == 'edit':
                    print(f"\n✏️  Edit comment (press Enter to keep current):")
                    new_content = input(f"   > ").strip()
                    if new_content:
                        current_content = new_content
                        print(f"   ✅ Updated to: \"{current_content}\"")
                    else:
                        print("   ℹ️  Kept original content")
                    # 继续循环，再次确认

                elif confirm == 's' or confirm == 'skip':
                    print("   ⏭️  Skipped")
                    break

                elif confirm == 'q' or confirm == 'quit':
                    print("\n🛑 Quit publishing")
                    print(f"\n✅ Successfully published {success_count}/{i-1} comment(s)")
                    return

                else:
                    print("   Invalid input. Please enter y/e/s/q")

        print(f"\n{'='*80}")
        print(f"✅ Successfully published {success_count}/{len(approved)} comment(s)")

    def show_stats(self):
        """显示统计信息"""
        print("\n📊 Argo Growth Statistics")
        print("=" * 80)

        # 评论统计
        stats = self.store.get_comment_stats()
        print("\n💬 Comments:")
        print(f"   Pending:   {stats['pending']}")
        print(f"   Approved:  {stats['approved']}")
        print(f"   Published: {stats['published']}")
        print(f"   Rejected:  {stats['rejected']}")

        # 最近发布
        recent_1h = self.store.get_recent_published_count(hours=1)
        recent_24h = self.store.get_recent_published_count(hours=24)
        print(f"\n📈 Recent Activity:")
        print(f"   Last 1 hour:  {recent_1h} published")
        print(f"   Last 24 hours: {recent_24h} published")

        # 大V列表
        influencers = self.store.load_influencers()
        print(f"\n👥 Influencers: {len(influencers)}")

        print("=" * 80)


def main():
    """CLI入口"""
    parser = argparse.ArgumentParser(
        description='Argo Growth - X/Twitter Growth Automation'
    )

    parser.add_argument(
        'command',
        choices=['scan', 'review', 'publish', 'stats', 'auth'],
        help='Command to run'
    )

    parser.add_argument(
        '--config-dir',
        type=Path,
        help='Configuration directory (default: ./argo/growth/config)'
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        help='Data storage directory (default: ./argo/growth/data)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (show browser window)'
    )

    parser.add_argument(
        '--no-cdp',
        action='store_true',
        help='Disable CDP mode (use agent-browser without real Chrome connection)'
    )

    args = parser.parse_args()

    try:
        # 如果是 debug 模式，使用 headed browser
        if args.debug:
            print("🐛 Debug mode enabled - browser window will be visible")

        # CDP 模式默认启用（推荐），除非用户明确禁用
        use_cdp = not args.no_cdp
        if use_cdp:
            print("🔌 CDP mode enabled - will connect to real Chrome")
            print("   Make sure Chrome is running with: --remote-debugging-port=9222")
            print("   See SETUP_TWITTER_REAL_CHROME.md for setup instructions")

        app = YouGen(
            config_dir=args.config_dir,
            data_dir=args.data_dir,
            debug=args.debug,
            use_cdp=use_cdp
        )

        if args.command == 'auth':
            app.check_auth()

        elif args.command == 'scan':
            if not app.check_auth():
                return
            asyncio.run(app.scan_and_generate())

        elif args.command == 'review':
            if not app.check_auth():
                return
            app.review_comments()

        elif args.command == 'publish':
            if not app.check_auth():
                return
            app.publish_approved()

        elif args.command == 'stats':
            app.show_stats()

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except BirdClientError as e:
        print(f"❌ Bird CLI Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
