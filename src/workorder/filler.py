"""
工单表单填充器
根据提取的数据填充工单表单
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from ..core.config_loader import ConfigLoader
from ..core.exceptions import TicketSystemError
from .browser import TicketBrowser
from .handlers import FieldHandlerFactory


class TicketSystemFiller:
    """工单表单填充器"""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.config_loader = config_loader or ConfigLoader()
        self.field_config = self.config_loader.load_field_mapping()
        self.settings = self.config_loader.load_settings()

        self.browser = TicketBrowser(config_loader)
        self.fields: List[Dict[str, Any]] = []
        self._load_fields()

    def _load_fields(self) -> None:
        """加载字段配置"""
        ticket_system = self.field_config.get("ticket_system", {})
        self.fields = ticket_system.get("fields", [])
        logger.info(f"已加载 {len(self.fields)} 个字段配置")

    async def open(self, url: Optional[str] = None) -> None:
        """打开工单系统"""
        await self.browser.initialize()
        await self.browser.open(url)

    async def login(self, username: str, password: str) -> None:
        """登录工单系统"""
        ticket_system = self.field_config.get("ticket_system", {})
        if ticket_system.get("login_required", True):
            await self.browser.login(username, password)

    async def fill_field(self, field: Dict[str, Any], value: Any) -> None:
        """
        填充单个字段

        Args:
            field: 字段配置
            value: 值
        """
        field_type = field.get("type", "text")
        handler = FieldHandlerFactory.create(field_type, self.browser)

        try:
            await handler.handle(field, value)
        except Exception as e:
            logger.warning(f"填充字段 {field.get('name')} 失败: {e}")
            raise TicketSystemError(f"填充字段失败: {field.get('name')}: {e}")

    async def fill_all(self, data: Dict[str, Any]) -> None:
        """
        根据提取的数据填充所有字段

        Args:
            data: 提取的数据（字典）
        """
        logger.info(f"开始填充表单，数据: {data}")

        fill_delay = self.settings.get("workorder", {}).get("fill_delay", 1)

        for field in self.fields:
            field_name = field.get("name", "")
            source = field.get("source", "input")
            extract_key = field.get("extract_key", "")

            try:
                if source == "input":
                    # 手动输入的值（来自默认值或其他）
                    value = field.get("default", "")
                elif source == "extracted":
                    # 从提取数据中获取
                    value = data.get(extract_key, "")
                else:
                    value = ""

                if value:
                    await self.fill_field(field, value)
                    await self.browser.page.wait_for_timeout(fill_delay * 1000)

            except Exception as e:
                logger.warning(f"填充字段 {field_name} 时出错: {e}")
                # 继续填充其他字段

        logger.info("表单填充完成")

    async def submit(self) -> None:
        """提交工单"""
        # 查找提交按钮
        # 注意：需要根据实际工单系统调整
        submit_selectors = [
            "button[type='submit']",
            ".btn-submit",
            "[class*='submit']",
            "button:has-text('提交')",
            "button:has-text('确定')",
        ]

        for selector in submit_selectors:
            try:
                if await self.browser.wait_for_selector(selector, timeout=3000):
                    await self.browser.click(selector)
                    logger.info("工单已提交")
                    return
            except Exception:
                continue

        logger.warning("未找到提交按钮")

    async def take_screenshot(self, path: str) -> None:
        """截取当前页面"""
        await self.browser.take_screenshot(path)

    async def close(self) -> None:
        """关闭浏览器"""
        await self.browser.close()
