"""
表单字段处理器
处理不同类型的表单字段填充
"""

from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .browser import TicketBrowser


class FieldHandler:
    """字段处理器基类"""

    def __init__(self, browser: TicketBrowser):
        self.browser = browser

    async def handle(self, field_config: Dict[str, Any], value: Any) -> None:
        """处理字段填充"""
        raise NotImplementedError


class TextFieldHandler(FieldHandler):
    """文本框处理器"""

    async def handle(self, field_config: Dict[str, Any], value: Any) -> None:
        selector = field_config.get("selector")
        multiline = field_config.get("multiline", False)

        if not selector:
            logger.warning(f"字段 {field_config.get('name')} 未配置 selector")
            return

        str_value = str(value) if value else ""

        if multiline:
            # 多行文本框，可能需要点击后输入
            await self.browser.click(selector)
            await self.browser.fill(selector, str_value)
        else:
            await self.browser.fill(selector, str_value)

        logger.debug(f"已填充文本框: {field_config.get('name')} = {str_value[:30]}...")


class DropdownFieldHandler(FieldHandler):
    """下拉框处理器"""

    async def handle(self, field_config: Dict[str, Any], value: Any) -> None:
        selector = field_config.get("selector")

        if not selector:
            logger.warning(f"字段 {field_config.get('name')} 未配置 selector")
            return

        str_value = str(value) if value else ""

        # 点击下拉框展开选项
        await self.browser.click(selector)

        # 等待选项出现
        await self.browser.wait_for_selector(f"{selector} option", timeout=5000)

        # 选择选项
        await self.browser.select_option(selector, value=str_value)

        logger.debug(f"已选择下拉选项: {field_config.get('name')} = {str_value}")


class PopupFieldHandler(FieldHandler):
    """弹窗选择处理器"""

    async def handle(self, field_config: Dict[str, Any], value: Any) -> None:
        selector = field_config.get("selector")
        popup_trigger = field_config.get("popup_trigger", selector)
        popup_selector = field_config.get("popup_selector")

        if not selector:
            logger.warning(f"字段 {field_config.get('name')} 未配置 selector")
            return

        str_value = str(value) if value else ""

        # 点击触发按钮打开弹窗
        await self.browser.click(popup_trigger)

        # 等待弹窗出现
        if popup_selector:
            await self.browser.wait_for_selector(popup_selector, timeout=5000)

            # 在弹窗内选择
            await self.browser.select_option(popup_selector, value=str_value)

            # 关闭弹窗（点击确定或其他方式）
            # 注意：具体实现可能需要根据弹窗结构调整
        else:
            logger.warning(f"字段 {field_config.get('name')} 未配置 popup_selector")

        logger.debug(f"已处理弹窗选择: {field_config.get('name')} = {str_value}")


class CheckboxFieldHandler(FieldHandler):
    """复选框处理器"""

    async def handle(self, field_config: Dict[str, Any], value: Any) -> None:
        selector = field_config.get("selector")

        if not selector:
            logger.warning(f"字段 {field_config.get('name')} 未配置 selector")
            return

        bool_value = bool(value)

        # 获取当前状态
        is_checked = await self.browser.page.is_checked(selector)

        # 如果状态不一致，则点击切换
        if is_checked != bool_value:
            await self.browser.click(selector)

        logger.debug(f"已设置复选框: {field_config.get('name')} = {bool_value}")


class FieldHandlerFactory:
    """字段处理器工厂"""

    HANDLERS: Dict[str, FieldHandler] = {
        "text": TextFieldHandler,
        "dropdown": DropdownFieldHandler,
        "popup": PopupFieldHandler,
        "checkbox": CheckboxFieldHandler,
    }

    @classmethod
    def create(cls, field_type: str, browser: TicketBrowser) -> FieldHandler:
        """
        创建字段处理器

        Args:
            field_type: 字段类型
            browser: 浏览器实例

        Returns:
            字段处理器
        """
        handler_class = cls.HANDLERS.get(field_type, TextFieldHandler)
        return handler_class(browser)
