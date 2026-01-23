"""CLI交互式评论审核"""

import asyncio
from typing import List, Optional
from yougen.storage.models import Tweet, Comment
from yougen.storage.file_store import FileStore
from yougen.core.bird_client import BirdClient
from yougen.core.browser_client import BrowserClient
from yougen.core.comment_generator import CommentGenerator


class Reviewer:
    """CLI评论审核器"""

    def __init__(
        self,
        store: FileStore,
        bird: BirdClient,
        browser: BrowserClient,
        generator: CommentGenerator,
        use_browser: bool = True
    ):
        self.store = store
        self.bird = bird
        self.browser = browser
        self.generator = generator
        self.use_browser = use_browser

    def display_tweet(self, tweet: Tweet, index: int, total: int):
        """显示推文信息"""
        print("\n" + "=" * 80)
        print(f"📊 Tweet {index}/{total}")
        print("=" * 80)
        print(f"👤 Author: @{tweet.author.username} ({tweet.author.name})")
        print(f"🆔 Tweet ID: {tweet.id}")
        print(f"⏰ Posted: {tweet.age_minutes():.1f} minutes ago")
        print(f"📈 Trend Score: {tweet.trending_score}/100")
        print(f"💬 Engagement: {tweet.like_count}❤️  {tweet.retweet_count}🔁  {tweet.reply_count}💬")
        print(f"\n📝 Content:\n{tweet.text}")
        print("-" * 80)

    def display_comment(self, comment: Comment):
        """显示评论"""
        print(f"\n💬 Generated Comment:")
        print(f"┌{'─' * 78}┐")
        print(f"│ {comment.content:<76} │")
        print(f"└{'─' * 78}┘")
        print(f"Length: {len(comment.content)} characters")

    async def review_single(
        self,
        tweet: Tweet,
        comment: Comment,
        index: int,
        total: int
    ) -> str:
        """
        审核单条评论

        Returns:
            'published': 已发布
            'approved': 已批准（稍后发布）
            'skipped': 跳过
            'quit': 退出审核
        """
        current_comment = comment

        while True:
            self.display_tweet(tweet, index, total)
            self.display_comment(current_comment)

            print("\n🎯 Actions:")
            print("  [p] Publish now (发布并继续)")
            print("  [a] Approve for later (批准稍后发布)")
            print("  [r] Refine comment (优化评论)")
            print("  [s] Skip this tweet (跳过)")
            print("  [q] Quit review (退出)")

            choice = input("\nYour choice: ").strip().lower()

            if choice == 'p':
                # 立即发布
                print("\n🚀 Publishing comment...")

                # 如果使用浏览器且是第一次发布，检查登录状态
                if self.use_browser and not hasattr(self, '_browser_checked'):
                    if not self.browser.ensure_logged_in():
                        print("❌ Please login to Twitter first")
                        print("Would you like to save it as 'approved' for later? [y/n]")
                        retry = input().strip().lower()
                        if retry == 'y':
                            self.store.update_comment_status(current_comment.id, 'approved')
                            return 'approved'
                        else:
                            self.store.update_comment_status(current_comment.id, 'rejected')
                            return 'skipped'
                    self._browser_checked = True

                # 构建tweet URL
                tweet_url = f"https://twitter.com/{tweet.author.username}/status/{tweet.id}"

                # 使用浏览器或bird CLI发布
                if self.use_browser:
                    success = self.browser.post_reply(tweet_url, current_comment.content)
                else:
                    success = self.bird.post_reply(tweet.id, current_comment.content)

                if success:
                    print("✅ Comment published successfully!")
                    self.store.update_comment_status(current_comment.id, 'published')
                    return 'published'
                else:
                    print("❌ Failed to publish comment.")
                    print("Would you like to save it as 'approved' for manual retry? [y/n]")
                    retry = input().strip().lower()
                    if retry == 'y':
                        self.store.update_comment_status(current_comment.id, 'approved')
                        return 'approved'
                    else:
                        self.store.update_comment_status(current_comment.id, 'rejected')
                        return 'skipped'

            elif choice == 'a':
                # 批准稍后发布
                self.store.update_comment_status(current_comment.id, 'approved')
                print("✅ Comment approved for later publishing")
                return 'approved'

            elif choice == 'r':
                # 优化评论
                print("\n✏️  How should I refine the comment?")
                print("Examples:")
                print("  - 更幽默一点")
                print("  - 去掉emoji")
                print("  - 更专业一些")
                print("  - 加入技术细节")
                feedback = input("\nYour feedback: ").strip()

                if not feedback:
                    print("⚠️  No feedback provided, skipping refinement")
                    continue

                print("\n🤖 Refining comment...")
                try:
                    refined = await self.generator.refine(current_comment, feedback)
                    self.store.save_comment(refined)

                    # 删除旧评论
                    self.store.delete_comment(current_comment.id)

                    # 更新当前评论
                    current_comment = refined
                    print("✅ Comment refined!")

                except Exception as e:
                    print(f"❌ Refinement failed: {e}")
                    print("Keeping original comment...")

            elif choice == 's':
                # 跳过
                self.store.update_comment_status(current_comment.id, 'rejected')
                print("⏭️  Tweet skipped")
                return 'skipped'

            elif choice == 'q':
                # 退出
                print("\n👋 Exiting review...")
                self.store.update_comment_status(current_comment.id, 'rejected')
                return 'quit'

            else:
                print("⚠️  Invalid choice, please try again")

    async def review_batch(self, tweet_comment_pairs: List[tuple[Tweet, Comment]]):
        """
        批量审核评论

        Args:
            tweet_comment_pairs: (推文, 评论) 对列表
        """
        if not tweet_comment_pairs:
            print("📭 No comments to review")
            return

        total = len(tweet_comment_pairs)
        print(f"\n🎯 Starting review of {total} comment(s)")
        print("=" * 80)

        stats = {
            'published': 0,
            'approved': 0,
            'skipped': 0,
            'quit': False
        }

        for i, (tweet, comment) in enumerate(tweet_comment_pairs, 1):
            result = await self.review_single(tweet, comment, i, total)

            if result == 'quit':
                stats['quit'] = True
                break
            elif result in stats:
                stats[result] += 1

        # 显示统计
        print("\n" + "=" * 80)
        print("📊 Review Summary")
        print("=" * 80)
        print(f"✅ Published: {stats['published']}")
        print(f"⏰ Approved for later: {stats['approved']}")
        print(f"⏭️  Skipped: {stats['skipped']}")

        if stats['quit']:
            remaining = total - (i - 1)
            print(f"🚪 Quit early ({remaining} remaining)")

        print("=" * 80)


def run_review(
    store: FileStore,
    bird: BirdClient,
    browser: BrowserClient,
    generator: CommentGenerator,
    use_browser: bool = True
):
    """运行审核流程（同步入口）"""
    # 加载待审核评论
    pending_comments = store.load_pending_comments()

    if not pending_comments:
        print("📭 No pending comments to review")
        return

    # 加载对应的推文
    pairs = []
    for comment in pending_comments:
        # 从comment的tweet_id直接用bird获取
        tweet = bird.get_tweet_by_id(comment.tweet_id)
        if tweet:
            pairs.append((tweet, comment))
        else:
            print(f"⚠️  Warning: Tweet {comment.tweet_id} not found, skipping comment")

    # 运行异步审核
    reviewer = Reviewer(store, bird, browser, generator, use_browser)
    asyncio.run(reviewer.review_batch(pairs))
