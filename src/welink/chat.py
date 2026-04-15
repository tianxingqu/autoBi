"""
Welink 聊天消息读取
读取群消息列表
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from ..core.exceptions import WelinkChatError, ElementNotFoundError
from ..core.config_loader import ConfigLoader
from .connector import WelinkConnector
from .locator import WelinkLocator


@dataclass
class Message:
    """消息结构"""

    sender: str  # 发送者
    content: str  # 内容
    timestamp: Optional[str] = None  # 时间戳
    is_self: bool = False  # 是否是自己发送的


class WelinkChat:
    """Welink 聊天功能"""

    def __init__(self, connector: WelinkConnector, config_loader: Optional[ConfigLoader] = None):
        self.connector = connector
        self.config_loader = config_loader or ConfigLoader()
        self.settings = self.config_loader.load_settings()
        self.welink_config = self.settings.get("welink", {})
        self.messages_config = self.welink_config.get("messages", {})
        self.locator: Optional[WelinkLocator] = None

    def _ensure_locator(self) -> WelinkLocator:
        """确保定位器已初始化"""
        if self.locator is None:
            app = self.connector.get_app()
            window = self.connector.get_window()
            self.locator = WelinkLocator(app, window)
        return self.locator

    def scroll_to_top(self) -> bool:
        """
        滚动到顶部加载历史消息

        Returns:
            bool: 是否成功
        """
        try:
            locator = self._ensure_locator()

            # 查找消息列表
            message_list = self._find_message_list()
            if not message_list:
                logger.warning("未找到消息列表")
                return False

            # 滚动到顶部
            # 注意：实际滚动实现可能需要根据 Welink 的具体控件调整
            for _ in range(10):
                message_list.type_keys("{HOME}")
                time.sleep(0.3)

            logger.debug("已滚动到顶部")
            return True

        except Exception as e:
            logger.warning(f"滚动到顶部失败: {e}")
            return False

    def _find_message_list(self) -> Any:
        """查找消息列表控件"""
        locator = self._ensure_locator()

        # 尝试多种方式查找消息列表
        strategies = [
            {"control_type": "List"},
            {"control_type": "Document"},  # 富文本控件
            {"title": ""},  # 通用的
        ]

        for criteria in strategies:
            try:
                message_list = locator.find_element(criteria, timeout=3)
                if message_list:
                    return message_list
            except ElementNotFoundError:
                continue

        raise WelinkChatError("未找到消息列表控件")

    def get_messages(self, count: int = 100) -> List[Message]:
        """
        获取消息列表

        Args:
            count: 预计获取的消息数量

        Returns:
            消息列表
        """
        logger.info(f"开始读取消息，预计数量: {count}")

        messages = []
        timeout = self.messages_config.get("timeout", 30)
        start_time = time.time()

        try:
            # 确保在聊天窗口
            self.connector.bring_to_front()
            time.sleep(1)

            # 滚动加载历史消息
            self._load_history_messages(count)

            # 读取消息
            locator = self._ensure_locator()
            message_list = self._find_message_list()

            # 获取所有消息项
            message_items = self._extract_message_items(message_list, count)

            for item in message_items:
                msg = self._parse_message_item(item)
                if msg:
                    messages.append(msg)

            logger.info(f"成功读取 {len(messages)} 条消息")
            return messages

        except Exception as e:
            logger.error(f"读取消息失败: {e}")
            raise WelinkChatError(f"读取消息失败: {e}")

    def _load_history_messages(self, target_count: int) -> None:
        """滚动加载历史消息"""
        scroll_step = self.messages_config.get("scroll_step", 50)
        loaded = 0

        locator = self._ensure_locator()

        for i in range(target_count // scroll_step + 1):
            try:
                # 滚动消息列表
                message_list = self._find_message_list()
                message_list.type_keys("{PGUP}")
                time.sleep(0.5)

                loaded += scroll_step
                logger.debug(f"已加载约 {loaded} 条消息")

            except Exception as e:
                logger.debug(f"滚动加载消息时出错: {e}")
                break

    def _extract_message_items(self, message_list: Any, max_count: int) -> List[Any]:
        """从消息列表中提取消息项"""
        items = []

        try:
            children = message_list.children()

            for child in children:
                try:
                    # 检查是否是消息项（通过控件类型或其他属性判断）
                    if self._is_message_item(child):
                        items.append(child)

                    # 递归检查子元素
                    if hasattr(child, 'children'):
                        sub_items = self._extract_message_items(child, max_count - len(items))
                        items.extend(sub_items)

                    if len(items) >= max_count:
                        break

                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"提取消息项时出错: {e}")

        return items[:max_count]

    def _is_message_item(self, element: Any) -> bool:
        """判断元素是否是消息项"""
        try:
            control_type = element.control_type

            # 消息项通常是 ListItem 或自定义控件
            if control_type in ["ListItem", "Custom", "Group"]:
                return True

            return False

        except Exception:
            return False

    def _parse_message_item(self, item: Any) -> Optional[Message]:
        """解析消息项"""
        try:
            # 获取消息文本
            text = item.window_text() or ""

            # 获取发送者
            sender = ""
            try:
                # 查找发送者控件
                sender_element = item.child_window(control_type="Text")
                if sender_element.exists(timeout=0):
                    sender = sender_element.window_text() or ""
            except Exception:
                pass

            # 过滤：只保留有内容的文本
            if not text.strip():
                return None

            # 创建消息对象
            msg = Message(
                sender=sender,
                content=text.strip(),
                timestamp=None,
                is_self=False
            )

            return msg

        except Exception as e:
            logger.debug(f"解析消息项失败: {e}")
            return None

    def extract_content(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        从消息列表中提取结构化内容

        Args:
            messages: 消息列表

        Returns:
            包含 content 字段的字典列表
        """
        extracted = []
        for msg in messages:
            extracted.append({
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "is_self": msg.is_self
            })
        return extracted
