"""
主题管理系统
支持多种皮肤/主题切换
"""

from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets
from loguru import logger

from ..core.config_loader import ConfigLoader

# 内置主题 QSS
THEME_QSS = {
    "light": """
        QMainWindow, QDialog {
            background-color: #f5f5f5;
        }
        QGroupBox {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            color: #333;
        }
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #bbb;
            border-radius: 4px;
            padding: 5px 15px;
            color: #333;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #aaa;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 4px;
            color: #333;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #5b9bd5;
        }
        QComboBox {
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 4px;
            color: #333;
        }
        QComboBox:hover {
            border: 1px solid #5b9bd5;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: white;
            border: 1px solid #ccc;
            selection-background-color: #5b9bd5;
        }
        QTableWidget, QListWidget {
            background-color: white;
            alternate-background-color: #f9f9f9;
            border: 1px solid #ccc;
            color: #333;
        }
        QTableWidget::item:selected, QListWidget::item:selected {
            background-color: #5b9bd5;
            color: white;
        }
        QTableWidget::item:hover, QListWidget::item:hover {
            background-color: #e8f0f8;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            color: #333;
            border: 1px solid #ccc;
            padding: 4px;
        }
        QLabel {
            color: #333;
        }
        QCheckBox {
            color: #333;
        }
        QCheckBox::indicator:checked {
            background-color: #5b9bd5;
            border: 1px solid #5b9bd5;
        }
        QScrollBar:vertical {
            border: none;
            background: #f0f0f0;
            width: 10px;
        }
        QScrollBar::handle:vertical {
            background: #c0c0c0;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        QScrollBar:horizontal {
            border: none;
            background: #f0f0f0;
            height: 10px;
        }
        QScrollBar::handle:horizontal {
            background: #c0c0c0;
            border-radius: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
            background: white;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #333;
            padding: 6px 12px;
            border: 1px solid #ccc;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 1px solid white;
        }
        QTabBar::tab:hover {
            background-color: #d0d0d0;
        }
        QSplitter::handle {
            background-color: #d0d0d0;
        }
        QProgressBar {
            border: 1px solid #ccc;
            border-radius: 4px;
            text-align: center;
            background-color: #f0f0f0;
        }
        QProgressBar::chunk {
            background-color: #5b9bd5;
            border-radius: 3px;
        }
        QMessageBox {
            background-color: #f5f5f5;
        }
    """,
    "blue": """
        QMainWindow, QDialog {
            background-color: #e8eef4;
        }
        QGroupBox {
            border: 1px solid #b0c4de;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            background-color: #f0f5fa;
        }
        QGroupBox::title {
            color: #2c5f8a;
        }
        QPushButton {
            background-color: #5b9bd5;
            border: 1px solid #4a8bc2;
            border-radius: 4px;
            padding: 5px 15px;
            color: white;
        }
        QPushButton:hover {
            background-color: #4a8bc2;
        }
        QPushButton:pressed {
            background-color: #3a6c9c;
        }
        QPushButton:disabled {
            background-color: #c0c0c0;
            color: #888;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: white;
            border: 1px solid #b0c4de;
            border-radius: 3px;
            padding: 4px;
            color: #333;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #5b9bd5;
        }
        QComboBox {
            background-color: white;
            border: 1px solid #b0c4de;
            border-radius: 3px;
            padding: 4px;
            color: #333;
        }
        QComboBox:hover {
            border: 1px solid #5b9bd5;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: white;
            border: 1px solid #b0c4de;
            selection-background-color: #5b9bd5;
        }
        QTableWidget, QListWidget {
            background-color: white;
            alternate-background-color: #f0f5fa;
            border: 1px solid #b0c4de;
            color: #333;
        }
        QTableWidget::item:selected, QListWidget::item:selected {
            background-color: #5b9bd5;
            color: white;
        }
        QTableWidget::item:hover, QListWidget::item:hover {
            background-color: #dce8f5;
        }
        QHeaderView::section {
            background-color: #c0d8f0;
            color: #2c5f8a;
            border: 1px solid #b0c4de;
            padding: 4px;
        }
        QLabel {
            color: #2c5f8a;
        }
        QCheckBox {
            color: #2c5f8a;
        }
        QCheckBox::indicator:checked {
            background-color: #5b9bd5;
            border: 1px solid #4a8bc2;
        }
        QScrollBar:vertical {
            border: none;
            background: #e0e8f0;
            width: 10px;
        }
        QScrollBar::handle:vertical {
            background: #8ab4d8;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #6a9ac8;
        }
        QScrollBar:horizontal {
            border: none;
            background: #e0e8f0;
            height: 10px;
        }
        QScrollBar::handle:horizontal {
            background: #8ab4d8;
            border-radius: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #b0c4de;
            background: white;
        }
        QTabBar::tab {
            background-color: #c0d8f0;
            color: #2c5f8a;
            padding: 6px 12px;
            border: 1px solid #b0c4de;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 1px solid white;
        }
        QTabBar::tab:hover {
            background-color: #d0e0f0;
        }
        QSplitter::handle {
            background-color: #b0c4de;
        }
        QProgressBar {
            border: 1px solid #b0c4de;
            border-radius: 4px;
            text-align: center;
            background-color: #f0f5fa;
        }
        QProgressBar::chunk {
            background-color: #5b9bd5;
            border-radius: 3px;
        }
        QMessageBox {
            background-color: #e8eef4;
        }
    """,
    "darkblue": """
        QMainWindow, QDialog {
            background-color: #1e2a38;
        }
        QGroupBox {
            border: 1px solid #3a4a5e;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            background-color: #252d3a;
        }
        QGroupBox::title {
            color: #7fa8d8;
        }
        QPushButton {
            background-color: #3a4a5e;
            border: 1px solid #4a5a6e;
            border-radius: 4px;
            padding: 5px 15px;
            color: #e0e8f0;
        }
        QPushButton:hover {
            background-color: #4a5a6e;
        }
        QPushButton:pressed {
            background-color: #2a3a4e;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #555;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2a3444;
            border: 1px solid #3a4a5e;
            border-radius: 3px;
            padding: 4px;
            color: #e0e8f0;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #5b7fb5;
        }
        QComboBox {
            background-color: #2a3444;
            border: 1px solid #3a4a5e;
            border-radius: 3px;
            padding: 4px;
            color: #e0e8f0;
        }
        QComboBox:hover {
            border: 1px solid #5b7fb5;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #2a3444;
            border: 1px solid #3a4a5e;
            selection-background-color: #5b7fb5;
        }
        QTableWidget, QListWidget {
            background-color: #1e2530;
            alternate-background-color: #252d3a;
            border: 1px solid #3a4a5e;
            color: #d0d8e0;
        }
        QTableWidget::item:selected, QListWidget::item:selected {
            background-color: #3a5070;
            color: white;
        }
        QTableWidget::item:hover, QListWidget::item:hover {
            background-color: #2a3a4e;
        }
        QHeaderView::section {
            background-color: #2a3a4e;
            color: #9ab8d8;
            border: 1px solid #3a4a5e;
            padding: 4px;
        }
        QLabel {
            color: #b8c8e0;
        }
        QCheckBox {
            color: #b8c8e0;
        }
        QCheckBox::indicator:checked {
            background-color: #5b7fb5;
            border: 1px solid #4a6a95;
        }
        QScrollBar:vertical {
            border: none;
            background: #1e2530;
            width: 10px;
        }
        QScrollBar::handle:vertical {
            background: #4a5a6e;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #5a6a7e;
        }
        QScrollBar:horizontal {
            border: none;
            background: #1e2530;
            height: 10px;
        }
        QScrollBar::handle:horizontal {
            background: #4a5a6e;
            border-radius: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #3a4a5e;
            background: #252d3a;
        }
        QTabBar::tab {
            background-color: #2a3a4e;
            color: #9ab8d8;
            padding: 6px 12px;
            border: 1px solid #3a4a5e;
        }
        QTabBar::tab:selected {
            background-color: #1e2530;
            border-bottom: 1px solid #1e2530;
        }
        QTabBar::tab:hover {
            background-color: #3a4a5e;
        }
        QSplitter::handle {
            background-color: #3a4a5e;
        }
        QProgressBar {
            border: 1px solid #3a4a5e;
            border-radius: 4px;
            text-align: center;
            background-color: #252d3a;
        }
        QProgressBar::chunk {
            background-color: #5b7fb5;
            border-radius: 3px;
        }
        QMessageBox {
            background-color: #1e2a38;
        }
    """
}

THEME_DISPLAY_NAMES = {
    "light": "浅色 (Light)",
    "blue": "蓝色 (Blue)",
    "darkblue": "深蓝 (Dark Blue)",
    "dark": "深色 (Dark)"
}


class ThemeManager:
    """主题管理器"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.current_theme = "light"
        self._load_theme_preference()

    def _load_theme_preference(self):
        """加载主题偏好"""
        try:
            config = self.config_loader.load("app-config")
            self.current_theme = config.get("theme", "light")
        except Exception:
            self.current_theme = "light"

    def save_theme_preference(self, theme: str):
        """保存主题偏好"""
        self.current_theme = theme
        config_path = self.config_loader.config_dir / "app-config.yaml"
        try:
            import yaml
            config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            config["theme"] = theme
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True)
        except Exception as e:
            logger.error(f"保存主题偏好失败: {e}")

    def get_theme_qss(self, theme: str) -> str:
        """获取主题 QSS"""
        if theme == "dark":
            try:
                import qdarkstyle
                return qdarkstyle.load_stylesheet_pyqt5()
            except ImportError:
                logger.warning("qdarkstyle 未安装，使用 darkblue 主题替代")
                return THEME_QSS.get("darkblue", "")
        return THEME_QSS.get(theme, THEME_QSS["light"])

    def apply_theme(self, app: QtWidgets.QApplication, theme: Optional[str] = None):
        """应用主题到应用"""
        if theme is None:
            theme = self.current_theme

        qss = self.get_theme_qss(theme)
        app.setStyleSheet(qss)
        self.current_theme = theme

    def get_available_themes(self) -> list:
        """获取可用的主题列表"""
        themes = ["light", "blue", "darkblue"]
        try:
            import qdarkstyle
            themes.append("dark")
        except ImportError:
            pass
        return themes

    def get_theme_display_name(self, theme: str) -> str:
        """获取主题显示名称"""
        return THEME_DISPLAY_NAMES.get(theme, theme)
