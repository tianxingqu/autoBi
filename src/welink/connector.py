"""
Welink 连接器
负责连接和管理 Welink 桌面客户端
"""

import time
from typing import Optional

from loguru import logger
from pywinauto import Application, WindowSpecification
from pywinauto.findwindows import find_window, ElementNotFoundError

from ..core.config_loader import ConfigLoader
from ..core.exceptions import WelinkConnectionError


class WelinkConnector:
    """Welink 连接器"""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.config_loader = config_loader or ConfigLoader()
        self.settings = self.config_loader.load_settings()
        self.welink_config = self.settings.get("welink", {})

        self.app: Optional[Application] = None
        self.main_window: Optional[WindowSpecification] = None
        self._connected = False

    def connect(self, timeout: int = 30) -> bool:
        """
        连接到 Welink 主窗口

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            bool: 连接是否成功
        """
        window_title = self.welink_config.get("window_title", "Welink")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 尝试连接到已运行的 Welink
                self.app = Application(backend="win32").connect(
                    title_re=f".*{window_title}.*",
                    timeout=5
                )
                self.main_window = self.app.window(title_re=f".*{window_title}.*")
                self._connected = True
                logger.info("已连接到 Welink 窗口")
                return True

            except ElementNotFoundError:
                # Welink 未运行，尝试启动
                logger.info("Welink 未运行，正在启动...")
                if self._start_welink():
                    continue
                time.sleep(2)

            except Exception as e:
                logger.warning(f"连接 Welink 失败: {e}")
                time.sleep(2)

        raise WelinkConnectionError(f"连接 Welink 超时（{timeout}秒）")

    def _start_welink(self) -> bool:
        """
        启动 Welink

        Returns:
            bool: 启动是否成功
        """
        executable_path = self.welink_config.get("executable_path")
        if not executable_path:
            logger.error("未配置 Welink 可执行文件路径")
            return False

        try:
            self.app = Application(backend="win32").start(executable_path)
            logger.info("Welink 启动命令已执行")
            return True
        except Exception as e:
            logger.error(f"启动 Welink 失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self.app:
            return False

        try:
            # 验证窗口是否仍然存在
            windows = self.app.windows()
            return len(windows) > 0
        except Exception:
            return False

    def get_window(self) -> WindowSpecification:
        """获取 Welink 主窗口对象"""
        if not self.is_connected():
            raise WelinkConnectionError("Welink 未连接")
        return self.main_window

    def get_app(self) -> Application:
        """获取 Application 对象"""
        if not self.app:
            raise WelinkConnectionError("Welink 未连接")
        return self.app

    def bring_to_front(self) -> None:
        """将 Welink 窗口置于前台"""
        if self.main_window:
            try:
                self.main_window.set_focus()
                self.main_window.restore()
                logger.debug("Welink 窗口已置于前台")
            except Exception as e:
                logger.warning(f"置顶 Welink 窗口失败: {e}")

    def close(self) -> None:
        """关闭 Welink 连接"""
        if self.app:
            try:
                self.app.kill()
                logger.info("Welink 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭 Welink 连接失败: {e}")
            finally:
                self._connected = False
                self.app = None
                self.main_window = None
