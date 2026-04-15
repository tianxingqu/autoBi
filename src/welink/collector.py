"""
Welink 收集器
负责截图和聊天记录收集
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..core.config_loader import ConfigLoader
from ..core.exceptions import WelinkConnectionError, WelinkChatError
from .connector import WelinkConnector
from .search import WelinkSearch
from .chat import WelinkChat, Message


class WelinkCollector:
    """Welink 数据收集器"""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.config_loader = config_loader or ConfigLoader()
        self.settings = self.config_loader.load_settings()

        self.connector = WelinkConnector(config_loader)
        self.search = WelinkSearch(self.connector)
        self.chat = WelinkChat(self.connector, config_loader)

        # 截图输出目录
        self.screenshot_dir = Path("data/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self._connected = False

    def connect(self, timeout: int = 30) -> bool:
        """
        连接 Welink

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 连接是否成功
        """
        if self._connected and self.connector.is_connected():
            return True

        self.connector.connect(timeout=timeout)
        self._connected = True
        logger.info("Welink 连接成功")
        return True

    def search_group(self, ticket_no: str) -> bool:
        """
        搜索工单群

        Args:
            ticket_no: 工单号

        Returns:
            bool: 搜索是否成功
        """
        return self.search.search_group(ticket_no)

    def take_screenshots(self, count: int = 10) -> List[str]:
        """
        截取聊天界面

        Args:
            count: 截图数量（会滚动聊天记录）

        Returns:
            截图文件路径列表
        """
        logger.info(f"开始截图，数量: {count}")
        screenshot_paths = []

        try:
            window = self.connector.get_window()

            # 激活窗口
            self.connector.bring_to_front()
            time.sleep(0.5)

            # 初始截图
            for i in range(count):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{i+1:02d}_{timestamp}.png"
                filepath = self.screenshot_dir / filename

                # 使用 pywinauto 截图
                self._capture_window(window, str(filepath))
                screenshot_paths.append(str(filepath))

                logger.debug(f"截图已保存: {filepath}")

                # 滚动聊天记录（最后一张不需要滚动）
                if i < count - 1:
                    self._scroll_chat()
                    time.sleep(0.3)

            logger.info(f"截图完成，共 {len(screenshot_paths)} 张")
            return screenshot_paths

        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise WelinkChatError(f"截图失败: {e}")

    def _capture_window(self, window: Any, filepath: str) -> None:
        """
        截取窗口

        Args:
            window: 窗口对象
            filepath: 保存路径
        """
        try:
            # 方法1: 使用 pywinauto 的 capture_as_image
            from pywinauto import Desktop

            # 获取窗口句柄
            hwnd = window.handle

            # 使用 Windows API 截图
            import win32gui
            import win32ui
            import win32con
            from PIL import Image

            # 获取窗口位置和大小
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # 创建设备上下文
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # 创建位图
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # 截图
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

            # 保存为文件
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            img.save(filepath)

            # 释放资源
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

        except ImportError as e:
            logger.warning(f"截图依赖未安装: {e}")
            # 备用方法：使用窗口的 print 方法
            try:
                window.capture_as_image().save(filepath)
            except Exception as e2:
                logger.error(f"备用截图方法也失败: {e2}")
                raise

        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise

    def _scroll_chat(self) -> None:
        """滚动聊天记录"""
        try:
            # 使用 Page Up 键滚动
            from pywinauto import keyboard

            # 尝试多种滚动方式
            keyboard.send_keys("{PGUP}")
            time.sleep(0.2)

        except Exception as e:
            logger.debug(f"滚动失败: {e}")

    def get_messages(self, count: int = 50) -> List[Message]:
        """
        获取聊天记录

        Args:
            count: 预计获取的消息数量

        Returns:
            消息列表
        """
        logger.info(f"开始读取消息，预计数量: {count}")

        try:
            self.connector.bring_to_front()
            time.sleep(0.5)

            messages = self.chat.get_messages(count=count)

            logger.info(f"成功读取 {len(messages)} 条消息")
            return messages

        except Exception as e:
            logger.error(f"读取消息失败: {e}")
            raise WelinkChatError(f"读取消息失败: {e}")

    def close(self) -> None:
        """关闭连接"""
        try:
            self.connector.close()
            self._connected = False
            logger.info("Welink 连接已关闭")
        except Exception as e:
            logger.warning(f"关闭连接时出错: {e}")
