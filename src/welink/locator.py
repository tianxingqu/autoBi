"""
UI 元素定位器
提供多种策略定位 Welink UI 元素
"""

import time
from typing import Any, Callable, Optional

from loguru import logger
from pywinauto import Application, WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.findwindows import find_elements

from ..core.exceptions import ElementNotFoundError


class LocatorStrategy:
    """定位策略类型"""

    WINDOW_SPEC = "window_spec"  # 使用 pywinauto 窗口规格
    BEST_PRACTICE = "best_practice"  # 使用控件类型+文本
    IMAGE = "image"  # 图像识别（备用）


class WelinkLocator:
    """Welink UI 元素定位器"""

    def __init__(self, app: Application, window: WindowSpecification):
        self.app = app
        self.window = window
        self._cache = {}

    def find_element(
        self,
        criteria: dict,
        strategies: Optional[list] = None,
        timeout: int = 10
    ) -> UIAWrapper:
        """
        根据条件查找元素

        Args:
            criteria: 查找条件
                - auto_id: 自动化 ID
                - title: 标题
                - control_type: 控件类型
                - class_name: 类名
            strategies: 定位策略列表，按优先级尝试
            timeout: 超时时间（秒）

        Returns:
            找到的 UI 元素

        Raises:
            ElementNotFoundError: 元素未找到
        """
        strategies = strategies or [
            LocatorStrategy.WINDOW_SPEC,
            LocatorStrategy.BEST_PRACTICE,
        ]

        start_time = time.time()

        for strategy in strategies:
            if strategy == LocatorStrategy.WINDOW_SPEC:
                element = self._find_by_window_spec(criteria, timeout - (time.time() - start_time))
                if element:
                    return element

            elif strategy == LocatorStrategy.BEST_PRACTICE:
                element = self._find_by_best_practice(criteria, timeout - (time.time() - start_time))
                if element:
                    return element

            # 检查是否超时
            if time.time() - start_time >= timeout:
                break

        raise ElementNotFoundError(f"未找到元素: {criteria}")

    def _find_by_window_spec(
        self, criteria: dict, timeout: int
    ) -> Optional[UIAWrapper]:
        """使用窗口规格查找"""
        try:
            # 构建子窗口规格
            spec = self.window

            if criteria.get("auto_id"):
                spec = spec.child_window(auto_id=criteria["auto_id"])

            if criteria.get("title"):
                spec = spec.child_window(title=criteria["title"])

            if criteria.get("control_type"):
                spec = spec.child_window(control_type=criteria["control_type"])

            # 等待元素出现
            element = spec.wait("exists", timeout=timeout)
            logger.debug(f"通过 window_spec 找到元素: {criteria}")
            return element

        except Exception as e:
            logger.debug(f"window_spec 策略失败: {e}")
            return None

    def _find_by_best_practice(
        self, criteria: dict, timeout: int
    ) -> Optional[UIAWrapper]:
        """使用最佳实践查找（控件类型 + 文本）"""
        try:
            # 获取所有子元素
            children = self._get_all_children()

            for child in children:
                if self._matches_criteria(child, criteria):
                    logger.debug(f"通过 best_practice 找到元素: {criteria}")
                    return child

            return None

        except Exception as e:
            logger.debug(f"best_practice 策略失败: {e}")
            return None

    def _get_all_children(self) -> list:
        """获取所有子元素"""
        try:
            wrapper = self.window
            return wrapper.children()
        except Exception:
            return []

    def _matches_criteria(self, element: UIAWrapper, criteria: dict) -> bool:
        """检查元素是否匹配条件"""
        try:
            if criteria.get("control_type"):
                if element.control_type != criteria["control_type"]:
                    return False

            if criteria.get("title"):
                title = element.window_text() or ""
                if criteria["title"] not in title:
                    return False

            if criteria.get("class_name"):
                if element.class_name() != criteria["class_name"]:
                    return False

            return True

        except Exception:
            return False

    def find_by_text(self, text: str, control_type: Optional[str] = None) -> UIAWrapper:
        """
        通过文本查找元素

        Args:
            text: 元素文本
            control_type: 控件类型过滤

        Returns:
            找到的元素
        """
        criteria = {"title": text}
        if control_type:
            criteria["control_type"] = control_type
        return self.find_element(criteria)

    def find_by_auto_id(self, auto_id: str) -> UIAWrapper:
        """
        通过自动化 ID 查找元素

        Args:
            auto_id: 自动化 ID

        Returns:
            找到的元素
        """
        return self.find_element({"auto_id": auto_id})

    def click(self, element: UIAWrapper) -> None:
        """点击元素"""
        try:
            element.click()
            logger.debug(f"点击元素: {element.window_text() or element.auto_id}")
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            raise

    def double_click(self, element: UIAWrapper) -> None:
        """双击元素"""
        try:
            element.double_click()
            logger.debug(f"双击元素: {element.window_text() or element.auto_id}")
        except Exception as e:
            logger.error(f"双击元素失败: {e}")
            raise

    def input_text(self, element: UIAWrapper, text: str) -> None:
        """输入文本"""
        try:
            element.set_edit_text(text)
            logger.debug(f"输入文本: {text[:20]}...")
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            raise
