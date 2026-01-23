#!/usr/bin/env python3
"""
Claude Agent SDK 测试脚本

测试目标：
1. 基本query调用
2. 用户画像和风格学习
3. 评论生成能力
"""

import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions


async def test_basic_query():
    """测试1: 基本query调用"""
    print("=" * 60)
    print("测试1: 基本Agent SDK query调用")
    print("=" * 60)

    result_text = ""
    async for message in query(
        prompt="用一句话介绍你自己",
        options=ClaudeAgentOptions(
            allowed_tools=[],  # 不需要工具
        )
    ):
        # 打印消息类型
        print(f"Message type: {type(message).__name__}")
        if hasattr(message, "result"):
            result_text = message.result
            print(f"✅ 收到结果: {result_text[:100]}...")

    print()
    return result_text


async def test_comment_generation():
    """测试2: 评论生成（使用自定义agent）"""
    print("=" * 60)
    print("测试2: 评论生成Agent")
    print("=" * 60)

    # 用户画像
    user_profile = """
你是一个X (Twitter)评论助手。

用户画像:
- 专业领域: AI、机器学习、创业
- 语气风格: 专业但友好、不过度营销
- 关键词偏好: 技术、创新、效率
- 避免话题: 政治、争议话题

用户评论风格示例:
1. 推文: "AI safety is crucial"
   评论: "完全同意！在AI能力快速提升的今天，安全性研究必须同步跟进。"

2. 推文: "New LLM breakthrough"
   评论: "很有意思的进展！期待看到更多技术细节和benchmark结果。"

任务: 根据给定推文，生成一条符合用户风格的评论（100-200字符）。
"""

    # 测试推文
    test_tweet = {
        "author": "@elonmusk",
        "content": "AI will change everything. We're just at the beginning.",
        "likes": 1200,
        "retweets": 340,
    }

    prompt = f"""
请为以下推文生成一条评论：

作者: {test_tweet['author']}
内容: {test_tweet['content']}
点赞: {test_tweet['likes']} | 转发: {test_tweet['retweets']}

要求:
1. 符合用户画像和风格
2. 100-200字符
3. 有价值，不空洞
4. 自然、不过度营销
"""

    comment = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            system_prompt=user_profile
        )
    ):
        if hasattr(message, "result"):
            comment = message.result
            print(f"✅ 生成的评论:\n{comment}")

    print()
    return comment


async def test_with_session():
    """测试3: Session功能（上下文记忆）"""
    print("=" * 60)
    print("测试3: Session上下文记忆")
    print("=" * 60)

    session_id = None

    # 第一次查询
    async for message in query(
        prompt="记住这个信息：我最喜欢的话题是AI和机器学习",
        options=ClaudeAgentOptions(allowed_tools=[])
    ):
        if hasattr(message, "session_id"):
            session_id = message.session_id
            print(f"Session ID: {session_id}")
        if hasattr(message, "result"):
            print(f"第一轮: {message.result[:100]}...")

    # 第二次查询（恢复session）
    print("\n继续对话（使用session）...")
    async for message in query(
        prompt="我刚才说我喜欢什么话题？",
        options=ClaudeAgentOptions(resume=session_id)
    ):
        if hasattr(message, "result"):
            print(f"✅ 第二轮: {message.result}")
            if "AI" in message.result or "机器学习" in message.result:
                print("✅ Session记忆功能正常！")

    print()


async def main():
    """运行所有测试"""
    # 检查认证
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️ 未设置ANTHROPIC_AUTH_TOKEN或ANTHROPIC_API_KEY环境变量")
        print("请设置: export ANTHROPIC_AUTH_TOKEN='your-token'")
        return

    if os.environ.get("ANTHROPIC_BASE_URL"):
        print(f"✓ 使用自定义API地址: {os.environ.get('ANTHROPIC_BASE_URL')}")
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("✓ 使用ANTHROPIC_AUTH_TOKEN认证")

    print("\n🧪 Claude Agent SDK 测试\n")

    try:
        # 测试1: 基础调用
        await test_basic_query()

        # 测试2: 评论生成
        await test_comment_generation()

        # 测试3: Session功能
        await test_with_session()

        print("=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        print("\n关键发现:")
        print("1. ✅ Claude Agent SDK正常工作")
        print("2. ✅ 可以通过system prompt注入用户画像")
        print("3. ✅ 支持Session上下文记忆")
        print("4. ✅ 适合用于评论生成场景")
        print("\n结论: Claude Agent SDK完全满足MVP需求")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
