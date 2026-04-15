"""
字段配置编辑器
提供可视化界面配置工单字段映射
"""

from typing import Any, Dict, List, Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QTextEdit, QGroupBox, QCheckBox, QMessageBox, QListWidget,
    QListWidgetItem, QAbstractItemView, QSplitter, QTabWidget,
    QWidget, QFormLayout, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal

import yaml
from loguru import logger

from ..core.config_loader import ConfigLoader


class FieldEditor(QDialog):
    """单个字段编辑器"""

    FIELD_TYPES = ["text", "dropdown", "popup", "checkbox"]
    SOURCES = ["input", "extracted", "template"]
    SOURCE_LABELS = {
        "input": "手动输入",
        "extracted": "从消息提取",
        "template": "模板生成"
    }
    FIELD_TYPE_LABELS = {
        "text": "文本框",
        "dropdown": "下拉框",
        "popup": "弹窗选择",
        "checkbox": "复选框"
    }

    def __init__(self, field: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.field = field or {}
        self.setWindowTitle("编辑字段" if field else "新增字段")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self._init_ui()
        self._load_field()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("字段显示名称")
        basic_layout.addRow("字段名称:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([self.FIELD_TYPE_LABELS[t] for t in self.FIELD_TYPES])
        basic_layout.addRow("字段类型:", self.type_combo)

        self.selector_input = QLineEdit()
        self.selector_input.setPlaceholderText("CSS选择器或元素ID")
        basic_layout.addRow("选择器:", self.selector_input)

        # 来源配置
        source_group = QGroupBox("数据来源")
        source_layout = QVBoxLayout()
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        self.source_combo = QComboBox()
        self.source_combo.addItems([self.SOURCE_LABELS[s] for s in self.SOURCES])
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_layout.addWidget(QLabel("数据来源:"))
        source_layout.addWidget(self.source_combo)

        # 来源详情
        self.source_stack = QtWidgets.QStackedWidget()
        source_layout.addWidget(self.source_stack)

        # input 类型配置
        input_widget = QWidget()
        input_layout = QVBoxLayout()
        input_widget.setLayout(input_layout)
        self.default_input = QLineEdit()
        self.default_input.setPlaceholderText("默认值")
        input_layout.addWidget(QLabel("默认值:"))
        input_layout.addWidget(self.default_input)
        self.source_stack.addWidget(input_widget)

        # extracted 类型配置
        extracted_widget = QWidget()
        extracted_layout = QVBoxLayout()
        extracted_widget.setLayout(extracted_layout)
        self.extract_key_combo = QComboBox()
        self.extract_key_combo.addItems([
            "problem_type (问题类型)",
            "priority (优先级)",
            "host_ips (服务器IP)",
            "error_codes (错误码)",
            "ticket_refs (工单引用)",
            "description (问题描述)"
        ])
        extracted_layout.addWidget(QLabel("提取字段:"))
        extracted_layout.addWidget(self.extract_key_combo)
        self.source_stack.addWidget(extracted_widget)

        # template 类型配置
        template_widget = QWidget()
        template_layout = QVBoxLayout()
        template_widget.setLayout(template_layout)

        template_layout.addWidget(QLabel("模板内容 (可用变量 {problem_type}, {priority}, {host_ips}, 等):"))
        self.template_input = QTextEdit()
        self.template_input.setPlaceholderText(
            "问题类型：{problem_type}\n"
            "优先级：{priority}\n"
            "服务器IP：{host_ips}\n"
            "错误信息：{error_codes}"
        )
        self.template_input.setMinimumHeight(150)
        template_layout.addWidget(self.template_input)

        # 变量提示
        var_layout = QHBoxLayout()
        var_layout.addWidget(QLabel("快速插入变量:"))
        for var in ["{problem_type}", "{priority}", "{host_ips}", "{error_codes}"]:
            btn = QPushButton(var)
            btn.setMaximumWidth(100)
            btn.clicked.connect(lambda checked, v=var: self._insert_var(v))
            var_layout.addWidget(btn)
        var_layout.addStretch()
        template_layout.addLayout(var_layout)

        self.source_stack.addWidget(template_widget)

        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout()
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        self.multiline_check = QCheckBox("多行文本框")
        advanced_layout.addWidget(self.multiline_check)

        # 弹窗选择额外配置
        popup_group = QGroupBox("弹窗选择额外配置")
        popup_layout = QFormLayout()
        popup_group.setLayout(popup_layout)
        self.popup_trigger_input = QLineEdit()
        self.popup_trigger_input.setPlaceholderText("触发弹窗的按钮选择器")
        popup_layout.addRow("触发按钮:", self.popup_trigger_input)
        self.popup_selector_input = QLineEdit()
        self.popup_selector_input.setPlaceholderText("弹窗内的选择器")
        popup_layout.addRow("弹窗内选择器:", self.popup_selector_input)
        advanced_layout.addWidget(popup_group)

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_layout.addStretch()

        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

    def _load_field(self):
        """加载字段数据"""
        if not self.field:
            return

        self.name_input.setText(self.field.get("name", ""))

        # 类型
        field_type = self.field.get("type", "text")
        for i, t in enumerate(self.FIELD_TYPES):
            if t == field_type:
                self.type_combo.setCurrentIndex(i)
                break

        self.selector_input.setText(self.field.get("selector", ""))

        # 来源
        source = self.field.get("source", "input")
        for i, s in enumerate(self.SOURCES):
            if s == source:
                self.source_combo.setCurrentIndex(i)
                break

        if source == "input":
            self.default_input.setText(self.field.get("default", ""))
        elif source == "extracted":
            extract_key = self.field.get("extract_key", "")
            for i, key in enumerate(["problem_type", "priority", "host_ips", "error_codes", "ticket_refs", "description"]):
                if key == extract_key:
                    self.extract_key_combo.setCurrentIndex(i)
                    break
        elif source == "template":
            self.template_input.setText(self.field.get("template", ""))

        self.multiline_check.setChecked(self.field.get("multiline", False))
        self.popup_trigger_input.setText(self.field.get("popup_trigger", ""))
        self.popup_selector_input.setText(self.field.get("popup_selector", ""))

    def _on_source_changed(self, index):
        """来源变更"""
        self.source_stack.setCurrentIndex(index)

    def _insert_var(self, var: str):
        """插入变量"""
        self.template_input.insertPlainText(var)

    def get_field(self) -> Dict[str, Any]:
        """获取字段配置"""
        source = self.SOURCES[self.source_combo.currentIndex()]
        field_type = self.FIELD_TYPES[self.type_combo.currentIndex()]

        field = {
            "name": self.name_input.text(),
            "type": field_type,
            "selector": self.selector_input.text(),
            "source": source,
        }

        if source == "input":
            field["default"] = self.default_input.text()
        elif source == "extracted":
            field["extract_key"] = ["problem_type", "priority", "host_ips", "error_codes", "ticket_refs", "description"][self.extract_key_combo.currentIndex()]
        elif source == "template":
            field["template"] = self.template_input.toPlainText()

        if field_type == "popup":
            if self.popup_trigger_input.text():
                field["popup_trigger"] = self.popup_trigger_input.text()
            if self.popup_selector_input.text():
                field["popup_selector"] = self.popup_selector_input.text()

        if self.multiline_check.isChecked():
            field["multiline"] = True

        return field


class FieldConfigEditor(QDialog):
    """字段配置编辑器主窗口"""

    def __init__(self, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.config_loader = config_loader
        self.fields: List[Dict[str, Any]] = []

        self.setWindowTitle("字段配置编辑器")
        self.setModal(False)
        self.setMinimumSize(900, 600)
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 工具栏
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        self.btn_add = QPushButton("+ 添加字段")
        self.btn_add.clicked.connect(self._on_add_field)
        toolbar.addWidget(self.btn_add)

        self.btn_duplicate = QPushButton("复制字段")
        self.btn_duplicate.clicked.connect(self._on_duplicate_field)
        toolbar.addWidget(self.btn_duplicate)

        self.btn_delete = QPushButton("删除字段")
        self.btn_delete.clicked.connect(self._on_delete_field)
        toolbar.addWidget(self.btn_delete)

        toolbar.addStretch()

        self.btn_import = QPushButton("导入配置")
        self.btn_import.clicked.connect(self._on_import_config)
        toolbar.addWidget(self.btn_import)

        self.btn_export = QPushButton("导出配置")
        self.btn_export.clicked.connect(self._on_export_config)
        toolbar.addWidget(self.btn_export)

        # 字段列表
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：字段列表
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        left_layout.addWidget(QLabel("字段列表 (双击编辑):"))

        self.field_list = QListWidget()
        self.field_list.setAlternatingRowColors(True)
        self.field_list.itemDoubleClicked.connect(self._on_edit_field)
        left_layout.addWidget(self.field_list)

        # 右侧：预览
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        right_layout.addWidget(QLabel("配置预览:"))

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFontFamily("Consolas")
        right_layout.addWidget(self.preview_text)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_save = QPushButton("保存配置")
        self.btn_save.clicked.connect(self._on_save_config)
        btn_layout.addWidget(self.btn_save)

        btn_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

    def _load_config(self):
        """加载配置"""
        try:
            field_config = self.config_loader.load_field_mapping()
            self.fields = field_config.get("ticket_system", {}).get("fields", [])
            self._refresh_list()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.fields = []

    def _refresh_list(self):
        """刷新列表"""
        self.field_list.clear()
        for field in self.fields:
            name = field.get("name", "未命名")
            field_type = field.get("type", "text")
            source = field.get("source", "input")
            self.field_list.addItem(f"{name} [{field_type}] [{source}]")
        self._update_preview()

    def _update_preview(self):
        """更新预览"""
        config = {
            "ticket_system": {
                "url": "http://itsm.company.com",
                "fields": self.fields
            }
        }
        self.preview_text.setText(yaml.dump(config, allow_unicode=True, sort_keys=False))

    def _on_add_field(self):
        """添加字段"""
        editor = FieldEditor(parent=self)
        if editor.exec_() == QDialog.Accepted:
            field = editor.get_field()
            self.fields.append(field)
            self._refresh_list()

    def _on_edit_field(self, item):
        """编辑字段"""
        index = self.field_list.currentRow()
        if index < 0:
            return

        editor = FieldEditor(self.fields[index], parent=self)
        if editor.exec_() == QDialog.Accepted:
            self.fields[index] = editor.get_field()
            self._refresh_list()

    def _on_duplicate_field(self):
        """复制字段"""
        index = self.field_list.currentRow()
        if index < 0:
            QMessageBox.warning(self, "提示", "请先选择要复制的字段")
            return

        field = self.fields[index].copy()
        field["name"] = field["name"] + " (副本)"
        self.fields.append(field)
        self._refresh_list()

    def _on_delete_field(self):
        """删除字段"""
        index = self.field_list.currentRow()
        if index < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的字段")
            return

        reply = QMessageBox.question(
            self, "确认",
            f"确定删除字段「{self.fields[index].get('name', '')}」?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.fields.pop(index)
            self._refresh_list()

    def _on_import_config(self):
        """导入配置"""
        from PyQt5.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "YAML Files (*.yaml *.yml)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            fields = config.get("ticket_system", {}).get("fields", [])
            self.fields = fields
            self._refresh_list()
            QMessageBox.information(self, "成功", f"已导入 {len(fields)} 个字段")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败:\n{str(e)}")

    def _on_export_config(self):
        """导出配置"""
        from PyQt5.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "field-mapping.yaml", "YAML Files (*.yaml *.yml)"
        )
        if not path:
            return

        try:
            config = {
                "ticket_system": {
                    "url": "http://itsm.company.com",
                    "fields": self.fields
                }
            }
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)

            QMessageBox.information(self, "成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")

    def _on_save_config(self):
        """保存配置"""
        try:
            config = {
                "ticket_system": {
                    "url": "http://itsm.company.com",
                    "fields": self.fields
                }
            }

            config_path = self.config_loader.config_dir / "field-mapping.yaml"
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)

            # 清除缓存并重新加载
            self.config_loader.clear_cache()

            QMessageBox.information(self, "成功", f"配置已保存到\n{config_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")


def open_field_config_editor(config_loader: ConfigLoader, parent=None):
    """打开字段配置编辑器"""
    dialog = FieldConfigEditor(config_loader, parent)
    dialog.exec_()
