"""推文质量过滤器

实现两级过滤系统：
1. 快速规则过滤（同步，毫秒级）
2. AI语义分析（异步批量，秒级）
"""

import re
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from claude_agent_sdk import query

from yougen.storage.models import Tweet


@dataclass
class QualityFilterResult:
    """过滤结果"""
    passed: bool
    score: Optional[float] = None
    issues: List[str] = None
    reason: Optional[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class TweetQualityFilter:
    """推文质量过滤器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化过滤器

        Args:
            config: 过滤器配置
                - enabled: bool
                - rules: dict (min_text_length, filter_media_only, etc.)
                - ai_analysis: dict (enabled, min_quality_score, batch_size, etc.)
        """
        self.config = config
        self.rules_config = config.get('rules', {})
        self.ai_config = config.get('ai_analysis', {})

        # 规则配置
        self.min_text_length = self.rules_config.get('min_text_length', 20)
        self.filter_media_only = self.rules_config.get('filter_media_only', True)
        self.filter_reply_without_context = self.rules_config.get('filter_reply_without_context', True)
        self.filter_external_references = self.rules_config.get('filter_external_references', True)

        # AI配置
        self.ai_enabled = self.ai_config.get('enabled', True)
        self.min_quality_score = self.ai_config.get('min_quality_score', 60.0)
        self.batch_size = self.ai_config.get('batch_size', 5)
        self.max_concurrent = self.ai_config.get('max_concurrent', 3)
        self.model = self.ai_config.get('model', 'claude-sonnet-4-5-20250929')
        self.timeout_seconds = self.ai_config.get('timeout_seconds', 30)
        self.on_failure = self.ai_config.get('on_failure', 'pass')

    def filter_batch(self, tweets: List[Tweet]) -> Tuple[List[Tweet], List[Tweet]]:
        """批量过滤推文

        Args:
            tweets: 待过滤的推文列表

        Returns:
            (通过的推文列表, 被过滤的推文列表)
        """
        if not tweets:
            return [], []

        # 第一级：规则过滤
        passed_rules, filtered_rules = self._apply_rule_filters(tweets)

        # 第二级：AI过滤
        if self.ai_enabled and passed_rules:
            passed_ai, filtered_ai = asyncio.run(self._apply_ai_filters(passed_rules))
            all_filtered = filtered_rules + filtered_ai
            return passed_ai, all_filtered
        else:
            return passed_rules, filtered_rules

    def _apply_rule_filters(self, tweets: List[Tweet]) -> Tuple[List[Tweet], List[Tweet]]:
        """应用规则过滤（同步）

        Returns:
            (通过的推文, 被过滤的推文)
        """
        passed = []
        filtered = []

        for tweet in tweets:
            result = self._check_rules(tweet)
            if result.passed:
                passed.append(tweet)
            else:
                # 设置过滤原因
                tweet.filtered_reason = result.reason
                tweet.quality_issues = result.issues
                filtered.append(tweet)

        return passed, filtered

    def _check_rules(self, tweet: Tweet) -> QualityFilterResult:
        """检查单条推文的规则"""
        issues = []

        # 规则1：过滤仅包含媒体的推文
        if self.filter_media_only:
            clean_text = self._remove_urls_from_text(tweet.text)
            if len(tweet.media) > 0 and len(clean_text.strip()) < 10:
                issues.append("media_only")
                return QualityFilterResult(
                    passed=False,
                    reason="仅包含媒体，文本内容不足",
                    issues=issues
                )

        # 规则2：过滤无引用上文的回复
        if self.filter_reply_without_context:
            if tweet.is_reply and not tweet.has_quoted_content:
                clean_text = self._remove_urls_from_text(tweet.text)
                if not self._has_clear_context(clean_text):
                    issues.append("reply_without_context")
                    return QualityFilterResult(
                        passed=False,
                        reason="回复推文缺乏上下文",
                        issues=issues
                    )

        # 规则3：过滤过短的推文
        clean_text = self._remove_urls_from_text(tweet.text)
        if self._is_chinese_text(clean_text):
            # 中文：少于指定字数
            if len(clean_text) < self.min_text_length:
                issues.append("too_short")
                return QualityFilterResult(
                    passed=False,
                    reason=f"推文过短（<{self.min_text_length}字）",
                    issues=issues
                )
        else:
            # 英文：少于指定单词数
            words = clean_text.split()
            if len(words) < self.min_text_length:
                issues.append("too_short")
                return QualityFilterResult(
                    passed=False,
                    reason=f"推文过短（<{self.min_text_length}词）",
                    issues=issues
                )

        # 规则4：过滤模糊的外部引用
        if self.filter_external_references:
            if self._has_unclear_external_reference(tweet.text):
                issues.append("vague_reference")
                return QualityFilterResult(
                    passed=False,
                    reason="包含模糊的外部引用",
                    issues=issues
                )

        # 所有规则通过
        return QualityFilterResult(passed=True)

    async def _apply_ai_filters(self, tweets: List[Tweet]) -> Tuple[List[Tweet], List[Tweet]]:
        """应用AI过滤（异步批量）

        Returns:
            (通过的推文, 被过滤的推文)
        """
        passed = []
        filtered = []

        # 分批处理，每批并发分析
        for i in range(0, len(tweets), self.batch_size):
            batch = tweets[i:i + self.batch_size]

            # 创建并发任务
            tasks = [self._analyze_tweet_quality(tweet) for tweet in batch]

            # 限制并发数，使用gather并隔离异常
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for tweet, result in zip(batch, results):
                if isinstance(result, Exception):
                    # AI分析失败
                    if self.on_failure == 'pass':
                        passed.append(tweet)
                    else:
                        tweet.filtered_reason = f"AI分析失败: {str(result)}"
                        tweet.quality_issues = ["ai_error"]
                        filtered.append(tweet)
                elif result.passed:
                    tweet.quality_score = result.score
                    passed.append(tweet)
                else:
                    tweet.quality_score = result.score
                    tweet.quality_issues = result.issues
                    tweet.filtered_reason = result.reason
                    filtered.append(tweet)

        return passed, filtered

    async def _analyze_tweet_quality(self, tweet: Tweet) -> QualityFilterResult:
        """使用AI分析单条推文质量

        Returns:
            QualityFilterResult
        """
        system_prompt = self._build_ai_system_prompt()
        user_prompt = self._build_ai_user_prompt(tweet)

        try:
            # 使用Claude Agent SDK的query函数
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    query,
                    user_prompt,
                    system_prompt=system_prompt,
                    model=self.model
                ),
                timeout=self.timeout_seconds
            )

            # 解析响应
            result = self._parse_ai_response(response)
            return result

        except asyncio.TimeoutError:
            return QualityFilterResult(
                passed=False if self.on_failure == 'filter' else True,
                score=50.0,
                issues=["ai_timeout"],
                reason="AI分析超时"
            )
        except Exception as e:
            # 其他异常，根据配置决定是否通过
            if self.on_failure == 'pass':
                return QualityFilterResult(passed=True, score=None)
            else:
                return QualityFilterResult(
                    passed=False,
                    score=None,
                    issues=["ai_error"],
                    reason=f"AI分析异常: {str(e)}"
                )

    def _build_ai_system_prompt(self) -> str:
        """构建AI系统提示"""
        return """你是推文质量评估专家。你的任务是评估推文内容的质量，判断其是否适合作为评论目标。

评分标准：
- 90-100分: 优秀，内容完整、清晰、有价值
- 70-89分: 良好，基本满足要求，有轻微问题
- 50-69分: 一般，存在明显问题但可理解
- 30-49分: 较差，严重缺乏上下文或语义不清
- 0-29分: 极差，完全无法理解或无实质内容

关键问题标签：
- context_incomplete: 缺乏上下文，难以独立理解
- vague_references: 模糊指代，不知道"这个"、"那个"指什么
- low_information: 信息价值低，过于简单或空洞
- media_dependent: 过度依赖媒体/链接才能理解

请客观、一致地评估，输出标准JSON格式。"""

    def _build_ai_user_prompt(self, tweet: Tweet) -> str:
        """构建AI用户提示"""
        media_count = len(tweet.media)
        url_count = len(tweet.urls)
        is_reply_str = '是' if tweet.is_reply else '否'
        has_quoted_str = '是' if tweet.has_quoted_content else '否'

        return f"""请分析以下推文的内容质量：

推文内容：{tweet.text}

元数据：
- 是否为回复: {is_reply_str}
- 是否有引用: {has_quoted_str}
- 包含媒体: {media_count}个
- 包含链接: {url_count}个

请从以下维度评估：
1. 上下文完整性：内容是否可以独立理解，还是需要额外上下文？
2. 语义清晰度：表达是否清晰明确，避免模糊不清的指代？
3. 信息价值：是否包含实质性内容，而非纯粹的情绪表达或无意义的附和？
4. 独立性：是否过度依赖外部链接或媒体才能理解主旨？

请以JSON格式输出评估结果：
{{
    "score": 0-100的评分（整数）,
    "issues": ["问题1", "问题2"],
    "analysis": "简短分析说明（不超过100字）"
}}

只输出JSON，不要有其他内容。"""

    def _parse_ai_response(self, response: str) -> QualityFilterResult:
        """解析AI响应

        Args:
            response: AI返回的响应文本

        Returns:
            QualityFilterResult
        """
        import json

        try:
            # 尝试提取JSON
            # 有时AI会用markdown包裹JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                # 无法找到JSON，返回默认评分
                return QualityFilterResult(
                    passed=True,
                    score=50.0,
                    issues=["parse_error"],
                    reason="无法解析AI响应"
                )

            score = float(data.get('score', 50))
            issues = data.get('issues', [])
            analysis = data.get('analysis', '')

            # 判断是否通过
            passed = score >= self.min_quality_score

            return QualityFilterResult(
                passed=passed,
                score=score,
                issues=issues,
                reason=analysis if not passed else None
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # JSON解析失败，返回默认评分
            return QualityFilterResult(
                passed=True,
                score=50.0,
                issues=["parse_error"],
                reason=f"解析AI响应失败: {str(e)}"
            )

    # 辅助方法

    def _remove_urls_from_text(self, text: str) -> str:
        """移除文本中的URL"""
        # 匹配http/https链接
        url_pattern = r'https?://\S+'
        return re.sub(url_pattern, '', text).strip()

    def _is_chinese_text(self, text: str) -> bool:
        """判断文本主要是否为中文"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.strip())
        if total_chars == 0:
            return False
        return chinese_chars / total_chars > 0.3

    def _has_clear_context(self, text: str) -> bool:
        """检查文本是否有清晰的上下文

        判断标准：
        - 包含完整的主谓宾结构
        - 或包含明确的观点表达
        - 或包含具体的信息（数字、名称等）
        """
        # 简单启发式规则
        # 1. 文本足够长（>30字符）
        if len(text) > 30:
            return True

        # 2. 包含常见的观点词
        opinion_words = ['认为', '觉得', '同意', '反对', 'think', 'believe', 'agree', 'disagree']
        if any(word in text for word in opinion_words):
            return True

        # 3. 包含具体信息（数字、引号、问号）
        if re.search(r'\d+|"[^"]+"|？|\?', text):
            return True

        # 否则认为缺乏上下文
        return False

    def _has_unclear_external_reference(self, text: str) -> bool:
        """检查是否包含模糊的外部引用

        例如："这个太棒了"、"那个真的很有意思"等
        """
        # 检查以模糊指代开头的短句
        vague_patterns = [
            r'^这个[真太很]\w{1,3}',
            r'^那个[真太很]\w{1,3}',
            r'^它[真太很]\w{1,3}',
            r'^This is (so|very|really)',
            r'^That is (so|very|really)',
            r'^It is (so|very|really)',
        ]

        text = text.strip()
        for pattern in vague_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                # 检查是否在后文有解释
                if len(text) < 30:  # 太短，认为是模糊引用
                    return True

        return False
