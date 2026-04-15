"""
Welink 搜索功能
搜索工单群
"""

import time
from typing import Optional

from loguru import logger

from ..core.exceptions import WelinkSearchError, ElementNotFoundError
from .connector import WelinkConnector
from .locator import WelinkLocator, LocatorStrategy


class WelinkSearch:
    """Welink 搜索功能"""

    def __init__(self, connector: WelinkConnector):
        self.connector = connector
        self.locator: Optional[WelinkLocator] = None

    def _ensure_locator(self) -> WelinkLocator:
        """确保定位器已初始化"""
        if self.locator is None:
            app = self.connector.get_app()
            window = self.connector.get_window()
            self.locator = WelinkLocator(app, window)
        return self.locator

    def search_group(self, ticket_no: str, timeout: int = 30) -> bool:
        """
        搜索工单群

        Args:
            ticket_no: 工单号
            timeout: 超时时间（秒）

        Returns:
            bool: 搜索是否成功
        """
        logger.info(f"开始搜索工单群: {ticket_no}")
        self.connector.bring_to_front()

        try:
            # Step 1: 点击搜索按钮或搜索框
            if not self._click_search_box():
                logger.warning("无法点击搜索框，尝试其他方式")
                return False

            # Step 2: 输入工单号
            if not self._input_search_keyword(ticket_no, timeout):
                return False

            # Step 3: 等待搜索结果
            if not self._wait_for_search_results(timeout):
                logger.warning("未找到搜索结果")
                return False

            logger.info(f"搜索成功: {ticket_no}")
            return True

        except Exception as e:
            logger.error(f"搜索工单群失败: {e}")
            raise WelinkSearchError(f"搜索失败: {e}")

    def _click_search_box(self) -> bool:
        """点击搜索框"""
        try:
            locator = self._ensure_locator()

            # 尝试查找搜索框
            # 注意：实际 Welink 的控件结构需要通过 Spy++ 或 Inspect 分析
            search_box = locator.find_element(
                {"control_type": "Edit", "title": ""},
                timeout=5
            )
            locator.click(search_box)
            return True

        except ElementNotFoundError:
            # 尝试点击搜索图标按钮
            try:
                locator = self._ensure_locator()
                search_button = locator.find_element(
                    {"control_type": "Button", "title": "搜索"},
                    timeout=5
                )
                locator.click(search_button)
                return True
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"点击搜索框失败: {e}")

        return False

    def _input_search_keyword(self, keyword: str, timeout: int) -> bool:
        """输入搜索关键词"""
        try:
            locator = self._ensure_locator()

            # 查找搜索输入框
            search_input = locator.find_element(
                {"control_type": "Edit"},
                timeout=5
            )

            # 清空并输入
            locator.input_text(search_input, keyword)
            time.sleep(0.5)

            # 按回车键确认搜索
            search_input.type_keys("{ENTER}")

            logger.debug(f"已输入搜索关键词: {keyword}")
            return True

        except Exception as e:
            logger.error(f"输入搜索关键词失败: {e}")
            return False

    def _wait_for_search_results(self, timeout: int) -> bool:
        """等待搜索结果出现"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                locator = self._ensure_locator()

                # 查找搜索结果列表
                # 注意：实际控件结构需要分析
                results = locator.find_element(
                    {"control_type": "List"},
                    timeout=2
                )

                if results:
                    logger.debug("搜索结果已加载")
                    return True

            except ElementNotFoundError:
                time.sleep(0.5)
                continue

            except Exception as e:
                logger.debug(f"检查搜索结果时出错: {e}")
                time.sleep(0.5)

        return False

    def select_group(self, group_name: Optional[str] = None) -> bool:
        """
        选择并进入群聊

        Args:
            group_name: 群名称（如果为 None，选择第一个结果）

        Returns:
            bool: 是否成功进入群聊
        """
        try:
            locator = self._ensure_locator()

            # 查找搜索结果列表
            results_list = locator.find_element(
                {"control_type": "List"},
                timeout=5
            )

            # 获取列表项
            items = results_list.children()

            if not items:
                logger.warning("搜索结果为空")
                return False

            # 选择匹配的群或第一个结果
            target_item = None
            if group_name:
                for item in items:
                    if group_name in (item.window_text() or ""):
                        target_item = item
                        break

            if target_item is None and items:
                target_item = items[0]

            if target_item:
                locator.double_click(target_item)
                logger.info(f"已进入群聊: {target_item.window_text()}")
                return True

            return False

        except Exception as e:
            logger.error(f"选择群聊失败: {e}")
            return False
