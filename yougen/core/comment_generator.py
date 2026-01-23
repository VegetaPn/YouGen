"""评论生成器（使用Claude Agent SDK）"""

from claude_agent_sdk import query, ClaudeAgentOptions
from typing import Optional, Tuple
import asyncio
from yougen.storage.models import Tweet, Comment
from datetime import datetime, timezone
import uuid


class CommentGenerator:
    """评论生成器（使用Claude Agent SDK）"""

    def __init__(self, user_profile: dict):
        """
        Args:
            user_profile: 用户画像配置
        """
        self.user_profile = user_profile
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        profile = self.user_profile.get('profile', {})
        examples = self.user_profile.get('examples', [])

        # 格式化示例
        examples_text = '\n'.join([
            f"推文: \"{ex.get('tweet', '')}\"\n评论: \"{ex.get('comment', '')}\"\n"
            for ex in examples
        ])

        return f"""你是X (Twitter)评论助手。

用户画像:
- 专业领域: {', '.join(profile.get('expertise', []))}
- 语气风格: {profile.get('tone', '专业友好')}
- 关键词偏好: {', '.join(profile.get('keywords', []))}
- 避免话题: {', '.join(profile.get('avoid_keywords', []))}

评论风格示例:
{examples_text}

任务: 为X推文生成评论

要求:
1. 语言匹配: 评论必须使用与推文正文相同的语言（中文/英文/日文等）
2. 长度: 80-250字符（中文约40-120字）
3. 风格: 符合用户画像，有梗但不失专业
4. 内容: 有价值，不空洞，不过度营销
5. 自然: 像真人评论，可以用emoji但不要太多
6. 避免: 政治、争议话题、spam

CRITICAL - 输出格式:
- 只输出评论原文，不要有任何其他内容
- 不要加"评论："、"回复："等前缀
- 不要加引号、书名号
- 不要添加解释、说明
- 不要分行说明
- 就像你在 Twitter 上直接回复一样，只写评论本身
"""

    async def generate(self, tweet: Tweet) -> Comment:
        """
        生成单条评论

        Args:
            tweet: 推文对象

        Returns:
            生成的评论对象
        """
        prompt = f"""请为以下推文生成评论：

作者: @{tweet.author.username}
内容: {tweet.text}
互动数据: {tweet.like_count}赞 | {tweet.retweet_count}转发 | {tweet.reply_count}评论
趋势评分: {tweet.trending_score}/100

重要：评论必须使用与推文正文相同的语言（中文/英文/日文等）。
如果推文是英文，评论也用英文；如果推文是中文，评论也用中文。

生成一条符合我风格的评论。
"""

        content = ""
        session_id = None

        try:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    allowed_tools=[],
                    system_prompt=self.system_prompt,
                    model=self.user_profile.get('agent', {}).get('model', 'claude-opus-4-5-20251101')
                )
            ):
                if hasattr(message, "session_id"):
                    session_id = message.session_id
                if hasattr(message, "result"):
                    content = message.result
                    # Don't break - let the generator finish naturally

        except Exception as e:
            raise Exception(f"Failed to generate comment: {e}")

        # 清理评论内容（移除可能的前缀）
        content = self._clean_content(content)

        return Comment(
            id=str(uuid.uuid4()),
            tweet_id=tweet.id,
            content=content,
            generated_at=datetime.now(timezone.utc),
            status='pending',
            session_id=session_id,
            tweet_author=tweet.author.user_id
        )

    async def refine(
        self,
        comment: Comment,
        feedback: str
    ) -> Comment:
        """
        优化评论（使用Session保持上下文）

        Args:
            comment: 原评论对象
            feedback: 用户反馈

        Returns:
            优化后的新评论对象
        """
        if not comment.session_id:
            raise ValueError("Comment has no session_id, cannot refine")

        prompt = f"""原评论: "{comment.content}"

用户反馈: {feedback}

请根据反馈优化评论，保持风格一致。
"""

        refined_content = ""

        try:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    resume=comment.session_id
                )
            ):
                if hasattr(message, "result"):
                    refined_content = message.result
                    # Don't break - let the generator finish naturally

        except Exception as e:
            raise Exception(f"Failed to refine comment: {e}")

        # 清理内容
        refined_content = self._clean_content(refined_content)

        # 创建新评论对象
        return Comment(
            id=str(uuid.uuid4()),
            tweet_id=comment.tweet_id,
            content=refined_content,
            generated_at=datetime.now(timezone.utc),
            status='pending',
            session_id=comment.session_id,
            tweet_author=comment.tweet_author
        )

    async def generate_batch(
        self,
        tweets: list[Tweet],
        max_concurrent: int = 3
    ) -> list[Comment]:
        """
        批量生成评论（并发）

        Args:
            tweets: 推文列表
            max_concurrent: 最大并发数

        Returns:
            评论列表
        """
        comments = []

        # 分批处理
        for i in range(0, len(tweets), max_concurrent):
            batch = tweets[i:i + max_concurrent]
            print(f"🤖 Generating comments for {len(batch)} tweets...")

            # 并发生成
            tasks = [self.generate(tweet) for tweet in batch]
            batch_comments = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for j, result in enumerate(batch_comments):
                if isinstance(result, Exception):
                    print(f"   ❌ Failed to generate comment for tweet {batch[j].id}: {result}")
                else:
                    comments.append(result)
                    print(f"   ✅ Generated comment #{len(comments)}")

        return comments

    def _clean_content(self, content: str) -> str:
        """
        清理评论内容，只保留评论本身，去掉所有解释

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        if not content:
            return ""

        # 移除可能的前缀
        prefixes = [
            "评论：", "评论:", "Comment:", "回复：", "回复:",
            "生成的评论：", "生成的评论:",
            "**评论：**", "**评论:**",
            "这是一条", "这条评论", "我的评论是",
            "Here's", "Here is", "My comment:"
        ]

        for prefix in prefixes:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()

        # 如果包含冒号后跟引号，可能是 "解释：「评论内容」" 格式
        # 提取引号内的内容
        import re

        # 匹配 "xxx: 「评论」" 或 "xxx: "评论""
        match = re.search(r'[:：]\s*[「『"\'](.*?)[」』"\']', content)
        if match:
            content = match.group(1).strip()
        # 匹配 "「评论」" 开头
        elif content.startswith('「') or content.startswith('『'):
            match = re.match(r'^[「『](.*?)[」』]', content)
            if match:
                content = match.group(1).strip()

        # 移除可能的markdown格式
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith("'") and content.endswith("'"):
            content = content[1:-1]

        # 如果内容包含多行，且第一行是解释性文字，只取后面的
        lines = content.split('\n')
        if len(lines) > 1:
            # 如果第一行包含"评论"、"回复"等关键词，可能是解释
            first_line = lines[0].strip()
            if any(keyword in first_line for keyword in ['评论', '回复', 'comment', 'reply', '这是', '这条']):
                # 取第二行及之后的内容
                content = '\n'.join(lines[1:]).strip()

        # 移除可能的解释性后缀（比如 "（这样回复更友好）"）
        content = re.sub(r'[（(][^)）]*解释[^)）]*[)）]', '', content)
        content = re.sub(r'[（(][^)）]*说明[^)）]*[)）]', '', content)

        return content.strip()
