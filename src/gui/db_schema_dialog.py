"""
数据库表结构配置编辑器
提供可视化界面配置数据库表结构
"""

from typing import Any, Dict, List, Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QTextEdit, QGroupBox, QCheckBox, QMessageBox,
    QListWidget, QListWidgetItem, QSplitter,
    QWidget, QFormLayout, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt

import yaml
from loguru import logger

from ..core.config_loader import ConfigLoader


class ColumnEditor(QDialog):
    """列编辑器"""

    COLUMN_TYPES = ["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"]
    COLUMN_TYPE_LABELS = {
        "TEXT": "TEXT (文本)",
        "INTEGER": "INTEGER (整数)",
        "REAL": "REAL (小数)",
        "BLOB": "BLOB (二进制)",
        "NUMERIC": "NUMERIC (数字)"
    }

    def __init__(self, column: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.column = column or {}
        self.setWindowTitle("编辑列" if column else "新增列")
        self.setModal(True)
        self.setMinimumSize(450, 350)
        self._init_ui()
        self._load_column()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("列名称（如：title, priority）")
        basic_layout.addRow("列名:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([self.COLUMN_TYPE_LABELS[t] for t in self.COLUMN_TYPES])
        basic_layout.addRow("数据类型:", self.type_combo)

        # 约束
        constraint_group = QGroupBox("约束")
        constraint_layout = QVBoxLayout()
        constraint_group.setLayout(constraint_layout)
        layout.addWidget(constraint_group)

        self.pk_check = QCheckBox("主键 (PRIMARY KEY)")
        self.pk_check.stateChanged.connect(self._on_pk_changed)
        constraint_layout.addWidget(self.pk_check)

        self.autoinc_check = QCheckBox("自增 (AUTOINCREMENT)")
        constraint_layout.addWidget(self.autoinc_check)

        self.unique_check = QCheckBox("唯一 (UNIQUE)")
        constraint_layout.addWidget(self.unique_check)

        self.nullable_check = QCheckBox("可空 (NOT NULL)")
        self.nullable_check.setChecked(True)
        constraint_layout.addWidget(self.nullable_check)

        # 默认值
        default_group = QGroupBox("默认值")
        default_layout = QFormLayout()
        default_group.setLayout(default_layout)
        layout.addWidget(default_group)

        self.default_input = QLineEdit()
        self.default_input.setPlaceholderText("默认值（如：draft，CURRENT_TIMESTAMP）")
        default_layout.addRow("默认值:", self.default_input)

        # 描述
        desc_group = QGroupBox("其他")
        desc_layout = QFormLayout()
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("字段描述")
        desc_layout.addRow("描述:", self.desc_input)

        self.foreign_key_input = QLineEdit()
        self.foreign_key_input.setPlaceholderText("外键（如：workorders(id)）")
        desc_layout.addRow("外键:", self.foreign_key_input)

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

    def _load_column(self):
        """加载列数据"""
        if not self.column:
            return

        self.name_input.setText(self.column.get("name", ""))

        col_type = self.column.get("type", "TEXT")
        for i, t in enumerate(self.COLUMN_TYPES):
            if t == col_type:
                self.type_combo.setCurrentIndex(i)
                break

        self.pk_check.setChecked(self.column.get("primary_key", False))
        self.autoinc_check.setChecked(self.column.get("autoincrement", False))
        self.unique_check.setChecked(self.column.get("unique", False))
        self.nullable_check.setChecked(self.column.get("nullable", True))
        self.default_input.setText(self.column.get("default", ""))
        self.desc_input.setText(self.column.get("description", ""))
        self.foreign_key_input.setText(self.column.get("foreign_key", ""))

    def _on_pk_changed(self, state):
        """主键状态变更"""
        if state:
            self.nullable_check.setChecked(False)
            self.nullable_check.setEnabled(False)
        else:
            self.nullable_check.setEnabled(True)

    def get_column(self) -> Dict[str, Any]:
        """获取列配置"""
        column = {
            "name": self.name_input.text(),
            "type": self.COLUMN_TYPES[self.type_combo.currentIndex()],
        }

        if self.pk_check.isChecked():
            column["primary_key"] = True
        if self.autoinc_check.isChecked():
            column["autoincrement"] = True
        if self.unique_check.isChecked():
            column["unique"] = True
        if not self.nullable_check.isChecked():
            column["nullable"] = False
        if self.default_input.text():
            column["default"] = self.default_input.text()
        if self.desc_input.text():
            column["description"] = self.desc_input.text()
        if self.foreign_key_input.text():
            column["foreign_key"] = self.foreign_key_input.text()

        return column


class TableEditor(QDialog):
    """表编辑器"""

    def __init__(self, table_key: str, table_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.table_key = table_key
        self.table_config = table_config or {"columns": []}
        self.columns: List[Dict[str, Any]] = self.table_config.get("columns", [])

        self.setWindowTitle(f"编辑表: {table_key}")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 表信息
        info_layout = QHBoxLayout()
        layout.addLayout(info_layout)

        info_layout.addWidget(QLabel(f"表名: {self.table_key}"))

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("表描述")
        self.desc_input.setText(self.table_config.get("description", ""))
        info_layout.addWidget(QLabel("描述:"))
        info_layout.addWidget(self.desc_input)

        # 列列表
        layout.addWidget(QLabel("列定义:"))

        self.column_table = QTableWidget()
        self.column_table.setColumnCount(7)
        self.column_table.setHorizontalHeaderLabels(['列名', '类型', '主键', '自增', '唯一', '可空', '默认值'])
        self.column_table.setColumnWidth(0, 120)
        self.column_table.setColumnWidth(1, 120)
        self.column_table.setColumnWidth(2, 50)
        self.column_table.setColumnWidth(3, 50)
        self.column_table.setColumnWidth(4, 50)
        self.column_table.setColumnWidth(5, 50)
        self.column_table.setColumnWidth(6, 100)
        self.column_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.column_table.itemDoubleClicked.connect(self._on_edit_column)
        layout.addWidget(self.column_table)

        # 列操作按钮
        col_btn_layout = QHBoxLayout()
        layout.addLayout(col_btn_layout)

        self.btn_add_col = QPushButton("+ 添加列")
        self.btn_add_col.clicked.connect(self._on_add_column)
        col_btn_layout.addWidget(self.btn_add_col)

        self.btn_edit_col = QPushButton("编辑列")
        self.btn_edit_col.clicked.connect(self._on_edit_column)
        col_btn_layout.addWidget(self.btn_edit_col)

        self.btn_delete_col = QPushButton("删除列")
        self.btn_delete_col.clicked.connect(self._on_delete_column)
        col_btn_layout.addWidget(self.btn_delete_col)

        col_btn_layout.addStretch()

        # 上移/下移
        self.btn_move_up = QPushButton("↑ 上移")
        self.btn_move_up.clicked.connect(self._on_move_up)
        col_btn_layout.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("↓ 下移")
        self.btn_move_down.clicked.connect(self._on_move_down)
        col_btn_layout.addWidget(self.btn_move_down)

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_save)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        # 加载列
        self._refresh_column_table()

    def _refresh_column_table(self):
        """刷新列表格"""
        self.column_table.setRowCount(len(self.columns))

        for i, col in enumerate(self.columns):
            self.column_table.setItem(i, 0, QTableWidgetItem(col.get("name", "")))
            self.column_table.setItem(i, 1, QTableWidgetItem(col.get("type", "")))

            pk_item = QTableWidgetItem("✓" if col.get("primary_key") else "")
            pk_item.setTextAlignment(Qt.AlignCenter)
            self.column_table.setItem(i, 2, pk_item)

            autoinc_item = QTableWidgetItem("✓" if col.get("autoincrement") else "")
            autoinc_item.setTextAlignment(Qt.AlignCenter)
            self.column_table.setItem(i, 3, autoinc_item)

            unique_item = QTableWidgetItem("✓" if col.get("unique") else "")
            unique_item.setTextAlignment(Qt.AlignCenter)
            self.column_table.setItem(i, 4, unique_item)

            nullable_item = QTableWidgetItem("✓" if col.get("nullable", True) else "✗")
            nullable_item.setTextAlignment(Qt.AlignCenter)
            self.column_table.setItem(i, 5, nullable_item)

            self.column_table.setItem(i, 6, QTableWidgetItem(col.get("default", "")))

    def _on_add_column(self):
        """添加列"""
        editor = ColumnEditor(parent=self)
        if editor.exec_() == QDialog.Accepted:
            column = editor.get_column()
            if column.get("name"):
                self.columns.append(column)
                self._refresh_column_table()

    def _on_edit_column(self):
        """编辑列"""
        row = self.column_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要编辑的列")
            return

        editor = ColumnEditor(self.columns[row], parent=self)
        if editor.exec_() == QDialog.Accepted:
            self.columns[row] = editor.get_column()
            self._refresh_column_table()

    def _on_delete_column(self):
        """删除列"""
        row = self.column_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要删除的列")
            return

        col_name = self.columns[row].get("name", "")
        reply = QMessageBox.question(self, "确认", f"确定删除列「{col_name}」?")
        if reply == QMessageBox.Yes:
            self.columns.pop(row)
            self._refresh_column_table()

    def _on_move_up(self):
        """上移列"""
        row = self.column_table.currentRow()
        if row <= 0:
            return
        self.columns[row], self.columns[row - 1] = self.columns[row - 1], self.columns[row]
        self._refresh_column_table()
        self.column_table.selectRow(row - 1)

    def _on_move_down(self):
        """下移列"""
        row = self.column_table.currentRow()
        if row < 0 or row >= len(self.columns) - 1:
            return
        self.columns[row], self.columns[row + 1] = self.columns[row + 1], self.columns[row]
        self._refresh_column_table()
        self.column_table.selectRow(row + 1)

    def get_table_config(self) -> Dict[str, Any]:
        """获取表配置"""
        return {
            "table_name": self.table_key,
            "description": self.desc_input.text(),
            "columns": self.columns
        }


class DbSchemaEditor(QDialog):
    """数据库表结构编辑器"""

    def __init__(self, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.config_loader = config_loader
        self.schema: Dict[str, Any] = {}

        self.setWindowTitle("数据库表结构配置")
        self.setModal(False)
        self.setMinimumSize(900, 600)
        self._init_ui()
        self._load_schema()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 工具栏
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        self.btn_add_table = QPushButton("+ 添加表")
        self.btn_add_table.clicked.connect(self._on_add_table)
        toolbar.addWidget(self.btn_add_table)

        self.btn_edit_table = QPushButton("编辑表")
        self.btn_edit_table.clicked.connect(self._on_edit_table)
        toolbar.addWidget(self.btn_edit_table)

        self.btn_delete_table = QPushButton("删除表")
        self.btn_delete_table.clicked.connect(self._on_delete_table)
        toolbar.addWidget(self.btn_delete_table)

        toolbar.addStretch()

        self.btn_import = QPushButton("导入配置")
        self.btn_import.clicked.connect(self._on_import_config)
        toolbar.addWidget(self.btn_import)

        self.btn_export = QPushButton("导出配置")
        self.btn_export.clicked.connect(self._on_export_config)
        toolbar.addWidget(self.btn_export)

        # 表列表和预览
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：表列表
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        left_layout.addWidget(QLabel("表列表 (双击编辑):"))

        self.table_list = QListWidget()
        self.table_list.setAlternatingRowColors(True)
        self.table_list.itemDoubleClicked.connect(self._on_edit_table)
        left_layout.addWidget(self.table_list)

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
        splitter.setStretchFactor(1, 2)

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_save = QPushButton("保存配置")
        self.btn_save.clicked.connect(self._on_save_config)
        btn_layout.addWidget(self.btn_save)

        btn_layout.addStretch()

        self.btn_reload = QPushButton("重新加载")
        self.btn_reload.clicked.connect(self._load_schema)
        btn_layout.addWidget(self.btn_reload)

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

    def _load_schema(self):
        """加载表结构配置"""
        try:
            self.schema = self.config_loader.load("db-schema")
            self._refresh_table_list()
        except Exception as e:
            logger.error(f"加载表结构配置失败: {e}")
            self.schema = {"tables": {}}

    def _refresh_table_list(self):
        """刷新表列表"""
        self.table_list.clear()
        tables = self.schema.get("tables", {})
        for table_key, table_config in tables.items():
            table_name = table_config.get("table_name", table_key)
            desc = table_config.get("description", "")
            columns_count = len(table_config.get("columns", []))
            self.table_list.addItem(f"{table_name} ({columns_count}列) - {desc}")

        self._update_preview()

    def _update_preview(self):
        """更新预览"""
        self.preview_text.setText(yaml.dump(self.schema, allow_unicode=True, sort_keys=False))

    def _on_add_table(self):
        """添加表"""
        # 弹出输入对话框获取表名
        table_key, ok = QtWidgets.QInputDialog.getText(
            self, "添加表", "请输入表名（英文）:"
        )
        if not ok or not table_key:
            return

        # 检查是否已存在
        if table_key in self.schema.get("tables", {}):
            QMessageBox.warning(self, "错误", f"表「{table_key}」已存在")
            return

        editor = TableEditor(table_key, parent=self)
        if editor.exec_() == QDialog.Accepted:
            table_config = editor.get_table_config()
            self.schema.setdefault("tables", {})[table_key] = table_config
            self._refresh_table_list()

    def _on_edit_table(self, item=None):
        """编辑表"""
        if item is None:
            item = self.table_list.currentItem()
        if item is None:
            return

        row = self.table_list.currentRow()
        tables = list(self.schema.get("tables", {}).keys())
        if row < 0 or row >= len(tables):
            return

        table_key = tables[row]
        table_config = self.schema.get("tables", {}).get(table_key, {})

        editor = TableEditor(table_key, table_config, parent=self)
        if editor.exec_() == QDialog.Accepted:
            self.schema["tables"][table_key] = editor.get_table_config()
            self._refresh_table_list()

    def _on_delete_table(self):
        """删除表"""
        row = self.table_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要删除的表")
            return

        tables = list(self.schema.get("tables", {}).keys())
        table_key = tables[row]

        reply = QMessageBox.question(
            self, "确认",
            f"确定删除表「{table_key}」？\n这将同时删除该表的所有数据！",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.schema["tables"][table_key]
            self._refresh_table_list()

    def _on_import_config(self):
        """导入配置"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "导入配置", "", "YAML Files (*.yaml *.yml)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.schema = yaml.safe_load(f)
            self._refresh_table_list()
            QMessageBox.information(self, "成功", "配置已导入")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败:\n{str(e)}")

    def _on_export_config(self):
        """导出配置"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出配置", "db-schema.yaml", "YAML Files (*.yaml *.yml)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(self.schema, f, allow_unicode=True, sort_keys=False)
            QMessageBox.information(self, "成功", f"配置已导出到\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")

    def _on_save_config(self):
        """保存配置"""
        try:
            config_path = self.config_loader.config_dir / "db-schema.yaml"
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.schema, f, allow_unicode=True, sort_keys=False)

            # 清除缓存
            self.config_loader.clear_cache()

            QMessageBox.information(self, "成功", f"配置已保存到\n{config_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")


def open_db_schema_editor(config_loader: ConfigLoader, parent=None):
    """打开数据库表结构编辑器"""
    dialog = DbSchemaEditor(config_loader, parent)
    dialog.exec_()
