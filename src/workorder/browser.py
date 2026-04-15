"""
Playwright 浏览器封装
负责工单系统的浏览器操作
"""

import asyncio
from typing import Any, Dict, Optional

from loguru import logger
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from ..core.config_loader import ConfigLoader
from ..core.exceptions import TicketSystemError


class TicketBrowser:
    """工单系统浏览器管理"""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.config_loader = config_loader or ConfigLoader()
        self.field_config = self.config_loader.load_field_mapping()
        self.ticket_url = self.field_config.get("ticket_system", {}).get("url", "")

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._initialized = False

    async def initialize(self, headless: bool = False) -> None:
        """
        初始化浏览器

        Args:
            headless: 是否无头模式
        """
        if self._initialized:
            return

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            self.page = await self.context.new_page()

            # 设置默认超时
            self.page.set_default_timeout(30000)

            self._initialized = True
            logger.info("浏览器初始化成功")

        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            raise TicketSystemError(f"浏览器初始化失败: {e}")

    async def open(self, url: Optional[str] = None) -> None:
        """
        打开工单系统页面

        Args:
            url: 页面 URL（如果为 None，使用配置中的 URL）
        """
        if not self._initialized:
            await self.initialize()

        target_url = url or self.ticket_url
        if not target_url:
            raise TicketSystemError("未配置工单系统 URL")

        try:
            await self.page.goto(target_url)
            logger.info(f"已打开: {target_url}")
        except Exception as e:
            logger.error(f"打开页面失败: {e}")
            raise TicketSystemError(f"打开页面失败: {e}")

    async def login(self, username: str, password: str) -> None:
        """
        处理登录

        Args:
            username: 用户名
            password: 密码
        """
        if not self.page:
            raise TicketSystemError("浏览器未初始化")

        try:
            # 等待登录表单加载
            await self.page.wait_for_selector("input[type='text']", timeout=10000)

            # 输入用户名
            await self.page.fill("input[type='text']", username)

            # 输入密码
            await self.page.fill("input[type='password']", password)

            # 点击登录按钮
            await self.page.click("button[type='submit']")

            # 等待登录完成
            await self.page.wait_for_load_state("networkidle")

            logger.info("登录成功")

        except Exception as e:
            logger.error(f"登录失败: {e}")
            raise TicketSystemError(f"登录失败: {e}")

    async def wait_for_selector(
        self, selector: str, timeout: Optional[int] = None, state: str = "visible"
    ) -> bool:
        """
        等待元素出现

        Args:
            selector: CSS 选择器
            timeout: 超时时间（毫秒）
            state: 状态（visible, attached, hidden, detached）

        Returns:
            bool: 元素是否出现
        """
        if not self.page:
            raise TicketSystemError("浏览器未初始化")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout or 30000, state=state)
            return True
        except Exception:
            return False

    async def click(self, selector: str) -> None:
        """
        点击元素

        Args:
            selector: CSS 选择器
        """
        if not self.page:
            raise TicketSystemError("浏览器未初始化")

        try:
            await self.page.click(selector)
            logger.debug(f"点击: {selector}")
        except Exception as e:
            logger.error(f"点击失败: {selector} - {e}")
            raise TicketSystemError(f"点击失败: {e}")

    async def fill(self, selector: str, value: str) -> None:
        """
        填充文本框

        Args:
            selector: CSS 选择器
            value: 文本值
        """
        if not self.page:
            raise TicketSystemError("浏览器未初始化")

        try:
            await self.page.fill(selector, value)
            logger.debug(f"填充: {selector} = {value[:20]}...")
        except Exception as e:
            logger.error(f"填充失败: {selector} - {e}")
            raise TicketSystemError(f"填充失败: {e}")

    async def select_option(self, selector: str, value: str) -> None:
        """
        选择下拉框选项

        Args:
            selector: CSS 选择器
            value: 选项值
        """
        if not self.page:
            raise TicketSystemError("浏览器未初始化")

        try:
            await self.page.select_option(selector, value=value)
            logger.debug(f"选择: {selector} = {value}")
        except Exception as e:
            logger.error(f"选择失败: {selector} - {e}")
            raise TicketSystemError(f"选择失败: {e}")

    async def take_screenshot(self, path: str) -> None:
        """
        截图

        Args:
            path: 保存路径
        """
        if self.page:
            try:
                await self.page.screenshot(path=path)
                logger.debug(f"截图已保存: {path}")
            except Exception as e:
                logger.warning(f"截图失败: {e}")

    async def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self._initialized = False
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
