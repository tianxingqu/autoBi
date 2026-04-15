"""
设置对话框
提供主题选择和布局配置界面
"""

from typing import Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QComboBox, QCheckBox, QGroupBox,
    QFormLayout, QSlider, QValueLabel, QMessageBox
)
from PyQt5.QtCore import Qt

from ..core.config_loader import ConfigLoader
from .theme import ThemeManager
from .layout_settings import LayoutSettings


class ThemeSettingsWidget(QWidget):
    """主题设置页面"""

    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 主题选择
        group = QGroupBox("选择主题")
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        layout.addWidget(group)

        # 主题预览
        self.theme_combo = QComboBox()
        self._populate_theme_combo()
        group_layout.addWidget(QLabel("主题:"))
        group_layout.addWidget(self.theme_combo)

        # 预览区域
        preview_group = QGroupBox("主题预览")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # 预览标签
        self.preview_label = QLabel("预览区域")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(100)
        preview_layout.addWidget(self.preview_label)

        # 预览按钮和输入框
        preview_inputs = QHBoxLayout()
        preview_inputs.addWidget(QPushButton("按钮"))
        preview_inputs.addWidget(QtWidgets.QLineEdit("输入框"))
        preview_layout.addLayout(preview_inputs)

        preview_inputs2 = QHBoxLayout()
        preview_inputs2.addWidget(QCheckBox("复选框"))
        preview_inputs2.addWidget(QComboBox())
        preview_layout.addLayout(preview_inputs2)

        # 说明
        note = QLabel("提示: 主题变更会在点击「应用」或「确定」后生效")
        note.setStyleSheet("color: gray;")
        layout.addWidget(note)

        layout.addStretch()

        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

    def _populate_theme_combo(self):
        """填充主题下拉框"""
        themes = self.theme_manager.get_available_themes()
        for theme in themes:
            self.theme_combo.addItem(
                self.theme_manager.get_theme_display_name(theme),
                theme
            )
        # 设置当前主题
        current = self.theme_manager.current_theme
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current:
                self.theme_combo.setCurrentIndex(i)
                break

    def _on_theme_changed(self, index):
        """主题变更"""
        theme = self.theme_combo.itemData(index)
        qss = self.theme_manager.get_theme_qss(theme)
        self.preview_label.parent().setStyleSheet(qss)

    def get_selected_theme(self) -> str:
        """获取选中的主题"""
        return self.theme_combo.itemData(self.theme_combo.currentIndex())


class LayoutSettingsWidget(QWidget):
    """布局设置页面"""

    def __init__(self, layout_settings: LayoutSettings, parent=None):
        super().__init__(parent)
        self.layout_settings = layout_settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 主窗口布局
        mw_group = QGroupBox("主窗口布局")
        mw_layout = QFormLayout()
        mw_group.setLayout(mw_layout)
        layout.addWidget(mw_group)

        # splitter 比例设置说明
        mw_layout.addRow("分隔栏比例:", QLabel(
            "在主界面拖动分隔栏调整宽度，关闭设置时自动保存"
        ))

        # 面板可见性
        panel_group = QGroupBox("面板显示")
        panel_layout = QVBoxLayout()
        panel_group.setLayout(panel_layout)
        layout.addWidget(panel_layout)

        self.screenshot_check = QCheckBox("显示截图列表")
        self.screenshot_check.setChecked(
            self.layout_settings.get_panel_visible("screenshot_list")
        )
        panel_layout.addWidget(self.screenshot_check)

        self.chat_check = QCheckBox("显示聊天记录列表")
        self.chat_check.setChecked(
            self.layout_settings.get_panel_visible("chat_list")
        )
        panel_layout.addWidget(self.chat_check)

        # 重置按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_layout.addStretch()

        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)

        layout.addStretch()

    def _on_reset(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要重置所有布局设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.layout_settings.reset_to_default()
            self.screenshot_check.setChecked(True)
            self.chat_check.setChecked(True)
            QMessageBox.information(self, "成功", "已重置为默认设置")

    def save_settings(self):
        """保存设置"""
        self.layout_settings.save_panel_visible(
            "screenshot_list",
            self.screenshot_check.isChecked()
        )
        self.layout_settings.save_panel_visible(
            "chat_list",
            self.chat_check.isChecked()
        )


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.config_loader = config_loader
        self.theme_manager = ThemeManager(config_loader)
        self.layout_settings = LayoutSettings(config_loader)

        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 标签页
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 主题设置页
        self.theme_widget = ThemeSettingsWidget(self.theme_manager)
        self.tabs.addTab(self.theme_widget, "主题")

        # 布局设置页
        self.layout_widget = LayoutSettingsWidget(self.layout_settings)
        self.tabs.addTab(self.layout_widget, "布局")

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_apply = QPushButton("应用")
        self.btn_apply.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.btn_apply)

        btn_layout.addStretch()

        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

    def _on_apply(self):
        """应用设置"""
        # 保存主题
        selected_theme = self.theme_widget.get_selected_theme()
        self.theme_manager.save_theme_preference(selected_theme)

        # 保存布局
        self.layout_widget.save_settings()

        # 应用主题
        from .app import QApplication
        app = QApplication.instance()
        if app:
            self.theme_manager.apply_theme(app, selected_theme)

    def accept(self):
        """确定"""
        self._on_apply()
        super().accept()


def open_settings_dialog(config_loader: ConfigLoader, parent=None):
    """打开设置对话框"""
    dialog = SettingsDialog(config_loader, parent)
    dialog.exec_()
