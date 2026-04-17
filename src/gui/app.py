#!/usr/bin/env python3
"""
PyQt5 GUI 入口
运维工单自动化工具 - 图形界面
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from PyQt5 import QtWidgets

from src.core.config_loader import ConfigLoader
from src.core.logger import setup_logger
from src.database import Database
from src.gui.main_window import MainWindow
from src.gui.theme import ThemeManager


def main():
    """主函数"""
    # 初始化日志
    setup_logger(level="INFO")

    logger.info("启动运维工单自动化工具...")

    # 初始化组件
    config_loader = ConfigLoader(config_dir="config")
    db = Database(db_path="data/workorder.db")

    # 启动 GUI
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 风格，更现代

    # 应用主题
    theme_manager = ThemeManager(config_loader)
    theme_manager.apply_theme(app)

    window = MainWindow(db, config_loader)
    window.show()

    logger.info("GUI 已启动")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
