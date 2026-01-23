"""bird CLI封装客户端"""

from __future__ import annotations
import subprocess
import json
import time
from typing import List, Optional
from yougen.storage.models import Tweet


class BirdClientError(Exception):
    """bird CLI调用错误"""
    pass


class BirdRateLimitError(BirdClientError):
    """限流错误"""
    pass


class BirdClient:
    """bird CLI封装客户端"""

    def __init__(self, delay: float = 2.0):
        """
        Args:
            delay: 请求间隔（秒），防止限流
        """
        self.delay = delay
        self.last_call = 0

    def _rate_limit(self):
        """限流保护"""
        elapsed = time.time() - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()

    def _run_command(self, args: List[str], include_json=True) -> dict | str:
        """
        执行bird命令并返回结果

        Args:
            args: 命令参数列表
            include_json: 是否添加--json参数

        Returns:
            dict: JSON结果（如果include_json=True）
            str: 字符串结果（如果include_json=False）
        """
        self._rate_limit()

        command = ["bird"] + args
        if include_json:
            command.append("--json")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )

            if include_json:
                return json.loads(result.stdout)
            else:
                return result.stdout

        except subprocess.TimeoutExpired:
            raise BirdClientError(f"Command timed out: {' '.join(command)}")

        except subprocess.CalledProcessError as e:
            # 检查是否是限流错误
            if "rate limit" in e.stderr.lower() or "429" in e.stderr:
                raise BirdRateLimitError(f"Rate limited by X API: {e.stderr}")

            raise BirdClientError(f"Command failed: {e.stderr}")

        except json.JSONDecodeError as e:
            raise BirdClientError(f"Failed to parse JSON response: {e}")

        except FileNotFoundError:
            raise BirdClientError(
                "bird CLI not found. Install it with: brew install steipete/tap/bird"
            )

    def get_user_tweets(
        self,
        username: str,
        count: int = 20
    ) -> List[Tweet]:
        """
        获取用户推文

        Args:
            username: 用户名（可以带@或不带）
            count: 获取数量

        Returns:
            推文列表
        """
        # 移除@符号
        username = username.lstrip('@')

        try:
            data = self._run_command([
                "user-tweets",
                username,
                "-n", str(count)
            ])

            if not isinstance(data, list):
                raise BirdClientError(f"Unexpected response type: {type(data)}")

            return [Tweet.from_bird_json(t) for t in data]

        except BirdRateLimitError:
            # Re-raise rate limit errors without wrapping
            raise
        except Exception as e:
            raise BirdClientError(f"Failed to get tweets for @{username}: {e}")

    def search_tweets(
        self,
        query: str,
        count: int = 20
    ) -> List[Tweet]:
        """
        搜索推文

        Args:
            query: 搜索关键词
            count: 获取数量

        Returns:
            推文列表
        """
        try:
            data = self._run_command([
                "search",
                query,
                "-n", str(count)
            ])

            if not isinstance(data, list):
                raise BirdClientError(f"Unexpected response type: {type(data)}")

            return [Tweet.from_bird_json(t) for t in data]

        except BirdRateLimitError:
            # Re-raise rate limit errors without wrapping
            raise
        except Exception as e:
            raise BirdClientError(f"Failed to search tweets for '{query}': {e}")

    def post_reply(
        self,
        tweet_id: str,
        text: str
    ) -> bool:
        """
        发布评论

        Args:
            tweet_id: 推文ID
            text: 评论内容

        Returns:
            是否成功
        """
        try:
            self._run_command(
                ["reply", tweet_id, text],
                include_json=False
            )
            return True

        except BirdClientError as e:
            print(f"❌ Failed to post reply: {e}")
            return False

    def get_tweet_by_id(self, tweet_id: str) -> Optional[Tweet]:
        """
        获取单条推文详情

        Args:
            tweet_id: 推文ID

        Returns:
            推文对象或None
        """
        try:
            data = self._run_command(["read", tweet_id])

            if isinstance(data, dict):
                return Tweet.from_bird_json(data)
            else:
                raise BirdClientError(f"Unexpected response type: {type(data)}")

        except Exception as e:
            print(f"⚠️  Failed to get tweet {tweet_id}: {e}")
            return None

    def check_auth(self) -> tuple[bool, str]:
        """
        检查认证状态

        Returns:
            (是否认证成功, 用户名或错误信息)
        """
        try:
            result = self._run_command(["whoami"], include_json=False)

            # 解析输出获取用户名
            # 输出格式: "🙋 @username (Display Name)"
            if "@" in result:
                username = result.split("@")[1].split()[0]
                return True, username
            else:
                return False, "Unable to parse whoami output"

        except BirdClientError as e:
            return False, str(e)
