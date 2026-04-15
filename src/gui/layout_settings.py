"""
布局设置管理
保存和恢复用户界面布局偏好
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

import yaml
from loguru import logger

from ..core.config_loader import ConfigLoader


class LayoutSettings:
    """布局设置管理器"""

    DEFAULT_SETTINGS = {
        "main_window": {
            "width": 1000,
            "height": 700,
            "x": 100,
            "y": 100,
            "splitter_ratios": {
                "field_config": [1, 1],
                "db_schema": [1, 2]
            }
        },
        "toolbar_button_order": [
            "btn_add", "btn_refresh", "btn_export",
            "btn_field_config", "btn_db_config", "btn_settings"
        ],
        "panels_visible": {
            "screenshot_list": True,
            "chat_list": True
        }
    }

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self):
        """加载布局设置"""
        try:
            config = self.config_loader.load("layout")
            self.settings = config or {}
        except Exception as e:
            logger.warning(f"加载布局设置失败，使用默认值: {e}")
            self.settings = self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """保存布局设置"""
        try:
            config_path = self.config_loader.config_dir / "layout.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.settings, f, allow_unicode=True, sort_keys=False)
            logger.debug("布局设置已保存")
        except Exception as e:
            logger.error(f"保存布局设置失败: {e}")

    def get_main_window_geometry(self) -> Dict[str, int]:
        """获取主窗口几何信息"""
        mw = self.settings.get("main_window", {})
        return {
            "width": mw.get("width", 1000),
            "height": mw.get("height", 700),
            "x": mw.get("x", 100),
            "y": mw.get("y", 100)
        }

    def save_main_window_geometry(self, width: int, height: int, x: int, y: int):
        """保存主窗口几何信息"""
        self.settings.setdefault("main_window", {})
        self.settings["main_window"]["width"] = width
        self.settings["main_window"]["height"] = height
        self.settings["main_window"]["x"] = x
        self.settings["main_window"]["y"] = y
        self.save_settings()

    def get_splitter_ratios(self, splitter_name: str) -> List[int]:
        """获取 splitter 比例"""
        ratios = self.settings.get("main_window", {}).get("splitter_ratios", {})
        return ratios.get(splitter_name, [1, 1])

    def save_splitter_ratios(self, splitter_name: str, sizes: List[int]):
        """保存 splitter 比例"""
        total = sum(sizes) if sum(sizes) > 0 else 1
        ratios = [s / total for s in sizes]
        self.settings.setdefault("main_window", {}).setdefault("splitter_ratios", {})
        self.settings["main_window"]["splitter_ratios"][splitter_name] = ratios
        self.save_settings()

    def get_toolbar_button_order(self) -> List[str]:
        """获取工具栏按钮顺序"""
        return self.settings.get("toolbar_button_order",
                                  self.DEFAULT_SETTINGS["toolbar_button_order"])

    def save_toolbar_button_order(self, order: List[str]):
        """保存工具栏按钮顺序"""
        self.settings["toolbar_button_order"] = order
        self.save_settings()

    def get_panel_visible(self, panel_name: str) -> bool:
        """获取面板可见性"""
        return self.settings.get("panels_visible", {}).get(panel_name, True)

    def save_panel_visible(self, panel_name: str, visible: bool):
        """保存面板可见性"""
        self.settings.setdefault("panels_visible", {})
        self.settings["panels_visible"][panel_name] = visible
        self.save_settings()

    def reset_to_default(self):
        """重置为默认设置"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.save_settings()
