"""Browser自动化客户端（用于发布评论）"""

from __future__ import annotations
import subprocess
import time
from typing import Optional
from pathlib import Path


class BrowserClientError(Exception):
    """Browser客户端错误"""
    pass


class BrowserClient:
    """Browser自动化客户端（使用agent-browser）"""

    def __init__(self, delay: float = 2.0, session_name: str = "", headed: bool = False, state_file: Optional[Path] = None, use_cdp: bool = False, cdp_port: int = 9222):
        """
        Args:
            delay: 操作间隔（秒）
            session_name: agent-browser会话名称（空字符串表示使用默认session）
            headed: 是否显示浏览器窗口（用于调试，CDP模式下忽略）
            state_file: 状态文件路径（保存登录状态，CDP模式下忽略）
            use_cdp: 是否使用CDP连接到真实Chrome浏览器（推荐，避免Twitter检测）
            cdp_port: CDP端口号（默认9222）
        """
        self.delay = delay
        self.session_name = session_name  # 空字符串表示不使用 --session 参数
        self.headed = headed
        self.state_file = state_file or Path.home() / ".argo" / "twitter_state.json"
        self.use_cdp = use_cdp
        self.cdp_port = cdp_port
        self.last_call = 0
        self._state_loaded = False

        # 确保状态文件目录存在（CDP模式下不需要）
        if not use_cdp:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self):
        """限流保护"""
        elapsed = time.time() - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()

    def _run_command(self, args: list[str], skip_rate_limit: bool = False) -> str:
        """
        执行agent-browser命令

        Args:
            args: 命令参数列表
            skip_rate_limit: 是否跳过限流（用于cleanup等操作）

        Returns:
            命令输出
        """
        if not skip_rate_limit:
            self._rate_limit()

        # 构建基础命令
        command = ["agent-browser"]

        # CDP 模式优先
        if self.use_cdp:
            command.extend(["--cdp", str(self.cdp_port)])
        else:
            # 只有指定了 session_name 才添加 --session 参数
            if self.session_name:
                if self.headed:
                    command.extend(["--session", self.session_name, "--headed"])
                else:
                    command.extend(["--session", self.session_name])
            else:
                # 使用默认 session
                if self.headed:
                    command.append("--headed")

        command.extend(args)

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            return result.stdout

        except subprocess.TimeoutExpired:
            raise BrowserClientError(f"Command timed out: {' '.join(command)}")

        except subprocess.CalledProcessError as e:
            raise BrowserClientError(f"Command failed: {e.stderr}")

        except FileNotFoundError:
            raise BrowserClientError(
                "agent-browser not found. Please install it first."
            )

    def _cleanup_stale_session(self):
        """清理可能存在的旧会话（避免"Browser not launched"错误）"""
        try:
            # 尝试关闭可能存在的旧会话
            self._run_command(["close"], skip_rate_limit=True)
            print("🧹 Cleaned up stale browser session")
        except:
            # 如果没有旧会话或关闭失败，忽略错误
            pass

    def _load_state_if_needed(self):
        """加载保存的状态（只加载一次）"""
        if self._state_loaded:
            return

        if not self.state_file.exists():
            session_cmd = f"agent-browser --session {self.session_name}" if self.session_name else "agent-browser"
            raise BrowserClientError(
                f"❌ Twitter session not found at: {self.state_file}\n\n"
                f"Please login first:\n"
                f"  1. {session_cmd} open https://twitter.com/login --headed\n"
                f"  2. Login manually in the browser\n"
                f"  3. {session_cmd} state save {self.state_file}\n"
                f"  4. {session_cmd} close\n\n"
                f"Then retry this command."
            )

        try:
            print(f"🔄 Loading saved session from: {self.state_file}")

            # 清理可能存在的旧会话
            self._cleanup_stale_session()

            # 先打开 Twitter 登录页启动浏览器
            print("🚀 Launching browser with Twitter login page...")
            self._run_command(["open", "https://twitter.com/login"])
            time.sleep(2)

            # 加载保存的状态（恢复登录）
            print("📥 Loading saved state...")
            self._run_command(["state", "load", str(self.state_file)])
            time.sleep(1)

            # 刷新页面使状态生效，并导航到主页
            print("🔐 Verifying login status...")
            self._run_command(["open", "https://twitter.com/home"])
            time.sleep(3)

            output = self._run_command(["snapshot", "-i"])

            # 检查是否真的登录了
            if "Log in" in output or "Sign in" in output or "登录" in output:
                print("\n⚠️  Session verification failed - not logged in")
                print(f"State file exists but login expired: {self.state_file}")
                session_cmd = f"agent-browser --session {self.session_name}" if self.session_name else "agent-browser"
                raise BrowserClientError(
                    f"❌ Login session expired or invalid.\n\n"
                    f"Please login again:\n"
                    f"  1. rm {self.state_file}\n"
                    f"  2. {session_cmd} open https://twitter.com/login --headed\n"
                    f"  3. Login manually and wait until you see your home feed\n"
                    f"  4. {session_cmd} state save {self.state_file}\n"
                    f"  5. {session_cmd} close\n\n"
                    f"Then retry."
                )

            self._state_loaded = True
            print("✅ Session loaded and verified - you are logged in!")

        except BrowserClientError:
            raise
        except Exception as e:
            raise BrowserClientError(f"Failed to load session state: {e}")

    def ensure_logged_in(self) -> bool:
        """
        确保已登录Twitter/X

        Returns:
            是否已登录
        """
        try:
            # CDP 模式下，假设用户已经在真实 Chrome 中登录
            if self.use_cdp:
                print(f"🔌 Using CDP mode - connecting to Chrome on port {self.cdp_port}")
                # 测试连接
                try:
                    current_url = self._run_command(["get", "url"])
                    print(f"✅ Connected to Chrome - Current URL: {current_url.strip()}")
                    return True
                except BrowserClientError as e:
                    print(f"❌ Failed to connect to Chrome on port {self.cdp_port}")
                    print(f"\nPlease start Chrome with CDP enabled:")
                    print(f"  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
                    print(f"    --remote-debugging-port={self.cdp_port} \\")
                    print(f"    --user-data-dir=\"$HOME/.argo/chrome-profile\" \\")
                    print(f"    https://twitter.com/login")
                    print(f"\nSee SETUP_TWITTER_REAL_CHROME.md for details.")
                    return False
            else:
                # 非 CDP 模式，使用 state 加载
                self._load_state_if_needed()
                return True
        except BrowserClientError as e:
            print(f"❌ {e}")
            return False

    def post_reply(self, tweet_url: str, text: str) -> bool:
        """
        发布评论到指定推文

        Args:
            tweet_url: 推文URL（格式：https://twitter.com/username/status/tweet_id）
            text: 评论内容

        Returns:
            是否成功
        """
        try:
            # CDP 模式下不需要加载状态，直接使用
            if not self.use_cdp:
                self._load_state_if_needed()

            print(f"\n🌐 Opening tweet: {tweet_url}")
            self._run_command(["open", tweet_url])
            time.sleep(3)  # 等待页面加载

            # 获取页面元素
            print("📸 Taking snapshot...")
            output = self._run_command(["snapshot", "-i"])

            # Debug 模式下才打印
            if self.headed:
                print("\n=== Snapshot Output (first 3000 chars) ===")
                print(output[:3000])
                print("=== End Snapshot ===\n")

            # 从 snapshot 中找到 textbox 的 ref
            print("✍️  Finding reply input box and filling text...")
            input_filled = False
            textbox_ref = None

            # 从输出中查找 textbox 的 ref（格式：textbox ... [ref=e123]）
            import re
            # 匹配 textbox "xxx" [ref=e123] 或 textbox [ref=e123]
            textbox_matches = re.findall(r'textbox[^\[]*\[ref=(e\d+)\]', output)

            if textbox_matches:
                textbox_ref = f"@{textbox_matches[0]}"
                print(f"   Found textbox: {textbox_ref}")

                # 使用 ref 填充内容
                try:
                    print(f"   Trying: fill {textbox_ref}")
                    self._run_command(["fill", textbox_ref, text])
                    input_filled = True
                    print("   ✅ Success!")
                except Exception as e:
                    print(f"   ❌ Failed: {str(e)[:100]}")
                    # 尝试 type 而不是 fill
                    try:
                        print(f"   Trying: type {textbox_ref}")
                        self._run_command(["type", textbox_ref, text])
                        input_filled = True
                        print("   ✅ Success!")
                    except Exception as e2:
                        print(f"   ❌ Failed: {str(e2)[:100]}")
            else:
                print("   ⚠️  No textbox found in snapshot")

            # 如果还是没成功，尝试 JavaScript 注入
            if not input_filled:
                try:
                    print("   Trying: JavaScript injection")
                    escaped_text = text.replace("'", "\\'").replace('"', '\\"')
                    self._run_command([
                        "eval",
                        f"document.querySelector('[contenteditable=\"true\"]').textContent = '{escaped_text}'"
                    ])
                    input_filled = True
                    print("   ✅ Success!")
                except Exception as e:
                    print(f"   ❌ Failed: {str(e)[:100]}")

            if not input_filled:
                raise BrowserClientError("Could not find or fill reply input box")

            time.sleep(1)

            # 发布回复 - 也使用 ref
            print("🚀 Posting reply...")
            post_success = False

            # 从 snapshot 中查找 Reply/Post 按钮（格式：button "Reply" [ref=e123]）
            button_patterns = [
                (r'button "Reply"[^\[]*\[ref=(e\d+)\]', 'Reply'),
                (r'button "Post reply"[^\[]*\[ref=(e\d+)\]', 'Post reply'),
                (r'button "Post"[^\[]*\[ref=(e\d+)\]', 'Post'),
                (r'button "回复"[^\[]*\[ref=(e\d+)\]', '回复'),
                (r'button "发布"[^\[]*\[ref=(e\d+)\]', '发布'),
            ]

            for pattern, name in button_patterns:
                matches = re.findall(pattern, output)
                if matches:
                    button_ref = f"@{matches[0]}"
                    try:
                        print(f"   Trying: click {button_ref} ({name})")
                        self._run_command(["click", button_ref])
                        post_success = True
                        print("   ✅ Success!")
                        break
                    except Exception as e:
                        print(f"   ❌ Failed: {str(e)[:100]}")

            if not post_success:
                raise BrowserClientError("Could not find Post/Reply button")

            time.sleep(3)  # 等待发布完成

            # 验证是否成功
            print("✅ Reply posted successfully!")
            return True

        except BrowserClientError as e:
            print(f"❌ Failed to post reply: {e}")
            if self.headed:
                print("\n⚠️  Browser window is still open for inspection")
                input("Press Enter to continue...")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if self.headed:
                print("\n⚠️  Browser window is still open for inspection")
                input("Press Enter to continue...")
            return False

    def close(self):
        """关闭浏览器会话"""
        # CDP 模式下不关闭浏览器，因为那是用户的真实 Chrome
        if self.use_cdp:
            print("ℹ️  CDP mode - not closing Chrome (it's your real browser)")
            return

        try:
            self._run_command(["close"])
        except:
            pass  # 忽略关闭错误
