"""
PyQt5 主窗口
工单列表和基本操作界面
"""

from pathlib import Path
from typing import Optional

from loguru import logger
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLabel, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QFileDialog, QProgressDialog, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from ..database import Database
from ..core.keyword_matcher import KeywordMatcher, MatchResult
from .collection_dialog import CollectionDialog
from .fill_dialog import AutoFillDialog


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, db: Database, config_loader):
        super().__init__()
        self.db = db
        self.config_loader = config_loader
        self.keyword_matcher = KeywordMatcher(config_loader)

        self.setWindowTitle("运维工单自动化工具")
        self.setGeometry(100, 100, 1000, 700)

        self._init_ui()
        self._refresh_table()

    def _init_ui(self):
        """初始化 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 工具栏
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        self.btn_add = QPushButton("新建工单")
        self.btn_add.clicked.connect(self._on_add_workorder)
        toolbar.addWidget(self.btn_add)

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self._refresh_table)
        toolbar.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("导出")
        self.btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(self.btn_export)

        toolbar.addStretch()

        # 工单列表
        self.table = QTableWidget()
        self.table.setColumns(['ID', '工单号', '标题', '状态', '优先级', '创建时间'])
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

    def _refresh_table(self):
        """刷新工单列表"""
        workorders = self.db.get_all_workorders()

        self.table.setRowCount(len(workorders))
        for i, wo in enumerate(workorders):
            self.table.setItem(i, 0, QTableWidgetItem(str(wo['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(wo['ticket_no'] or ''))
            self.table.setItem(i, 2, QTableWidgetItem(wo['title'] or ''))
            self.table.setItem(i, 3, QTableWidgetItem(wo['status'] or ''))
            self.table.setItem(i, 4, QTableWidgetItem(wo['priority'] or ''))
            self.table.setItem(i, 5, QTableWidgetItem(wo['created_at'] or ''))

    def _on_add_workorder(self):
        """添加工单"""
        dialog = AddWorkorderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            ticket_no = dialog.get_ticket_no()
            if ticket_no:
                # 创建工单
                workorder_id = self.db.create_workorder_simple(ticket_no, "")
                self._refresh_table()
                # 打开详情对话框
                self._open_workorder_detail(workorder_id)

    def _on_row_double_clicked(self, item):
        """双击行打开详情"""
        row = item.row()
        ticket_id = int(self.table.item(row, 0).text())
        self._open_workorder_detail(ticket_id)

    def _open_workorder_detail(self, ticket_id: int):
        """打开工单详情"""
        dialog = WorkorderDetailDialog(ticket_id, self.db, self.config_loader, self)
        dialog.exec_()
        self._refresh_table()

    def _on_export(self):
        """导出选中工单"""
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "提示", "请选择要导出的工单")
            return

        ticket_id = int(self.table.item(selected, 0).text())
        workorder = self.db.get_workorder(ticket_id)

        path, _ = QFileDialog.getSaveFileName(
            self, "导出工单", f"workorder_{workorder['ticket_no']}.json",
            "JSON Files (*.json)"
        )

        if path:
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(workorder, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", f"已导出到 {path}")


class AddWorkorderDialog(QDialog):
    """添加工单对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建工单")
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 工单号
        row = QHBoxLayout()
        layout.addLayout(row)
        row.addWidget(QLabel("工单号:"))
        self.ticket_no_input = QLineEdit()
        self.ticket_no_input.setPlaceholderText("输入工单号，如 ITSM-2024-00123")
        row.addWidget(self.ticket_no_input)

        # 按钮
        btns = QHBoxLayout()
        layout.addLayout(btns)
        btns.addStretch()
        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        btns.addWidget(self.btn_ok)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

    def get_ticket_no(self) -> str:
        return self.ticket_no_input.text().strip()


class WorkorderDetailDialog(QDialog):
    """工单详情对话框"""

    def __init__(self, ticket_id: int, db: Database, config_loader, parent=None):
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.db = db
        self.config_loader = config_loader
        self.workorder = db.get_workorder(ticket_id)

        self.setWindowTitle(f"工单详情 - {self.workorder['ticket_no']}")
        self.setModal(False)
        self.setGeometry(150, 150, 900, 700)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 工单基本信息
        info_group = QtWidgets.QGroupBox("工单信息")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 工单号
        row = QHBoxLayout()
        info_layout.addLayout(row)
        row.addWidget(QLabel("工单号:"))
        self.ticket_no_label = QLabel()
        row.addWidget(self.ticket_no_label)

        # 状态
        row.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(['draft', 'collecting', 'ready', 'submitted', 'completed'])
        row.addWidget(self.status_combo)
        self.status_combo.currentTextChanged.connect(self._on_status_changed)

        # 优先级
        row.addWidget(QLabel("优先级:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(['', 'P1', 'P2', 'P3', '紧急', '严重', '一般', '低'])
        row.addWidget(self.priority_combo)

        # 标题
        row = QHBoxLayout()
        info_layout.addLayout(row)
        row.addWidget(QLabel("标题:"))
        self.title_input = QLineEdit()
        row.addWidget(self.title_input)

        # 问题类型
        row = QHBoxLayout()
        info_layout.addLayout(row)
        row.addWidget(QLabel("问题类型:"))
        self.problem_type_combo = QComboBox()
        self.problem_type_combo.addItems(['', '服务器故障', '网络中断', '数据库异常', '应用不可用', '服务宕机'])
        row.addWidget(self.problem_type_combo)

        # 服务器IP
        row = QHBoxLayout()
        info_layout.addLayout(row)
        row.addWidget(QLabel("服务器IP:"))
        self.host_ip_input = QLineEdit()
        row.addWidget(self.host_ip_input)

        # 错误码
        row = QHBoxLayout()
        info_layout.addLayout(row)
        row.addWidget(QLabel("错误码:"))
        self.error_code_input = QLineEdit()
        row.addWidget(self.error_code_input)

        # 问题描述
        info_layout.addWidget(QLabel("问题描述:"))
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(100)
        info_layout.addWidget(self.description_input)

        # 操作按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_auto_collect = QPushButton("自动收集")
        self.btn_auto_collect.clicked.connect(self._on_auto_collect)
        btn_layout.addWidget(self.btn_auto_collect)

        self.btn_auto_fill = QPushButton("自动录单")
        self.btn_auto_fill.clicked.connect(self._on_auto_fill)
        btn_layout.addWidget(self.btn_auto_fill)

        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)

        btn_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        # 收集的截图标签页
        self.screenshot_label = QLabel("暂无截图")
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("收集的截图:"))
        self.screenshot_list = QtWidgets.QListWidget()
        self.screenshot_list.setMaximumHeight(150)
        layout.addWidget(self.screenshot_list)

        # 聊天记录标签页
        layout.addWidget(QLabel("聊天记录:"))
        self.chat_list = QtWidgets.QListWidget()
        layout.addWidget(self.chat_list)

    def _load_data(self):
        """加载数据"""
        wo = self.workorder
        if not wo:
            return

        self.ticket_no_label.setText(wo['ticket_no'] or '')

        idx = self.status_combo.findText(wo['status'] or 'draft')
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        idx = self.priority_combo.findText(wo['priority'] or '')
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)

        self.title_input.setText(wo['title'] or '')
        self.problem_type_combo.setCurrentText(wo['problem_type'] or '')
        self.host_ip_input.setText(wo['host_ips'] or '')
        self.error_code_input.setText(wo['error_codes'] or '')
        self.description_input.setText(wo['description'] or '')

        # 加载截图
        self._load_screenshots()

        # 加载聊天记录
        self._load_chat_messages()

    def _load_screenshots(self):
        """加载截图列表"""
        self.screenshot_list.clear()
        screenshots = self.db.get_screenshots(self.ticket_id)

        for ss in screenshots:
            item_text = f"[{'√' if ss['selected'] else ' '}] {Path(ss['file_path']).name}"
            self.screenshot_list.addItem(item_text)

    def _load_chat_messages(self):
        """加载聊天记录"""
        self.chat_list.clear()
        messages = self.db.get_chat_messages(self.ticket_id)

        for msg in messages:
            item_text = f"[{'√' if msg['selected'] else ' '}] {msg['sender']}: {msg['content'][:50]}..."
            self.chat_list.addItem(item_text)

    def _on_status_changed(self, status: str):
        """状态变更"""
        self.db.update_workorder(self.ticket_id, status=status)

    def _on_auto_collect(self):
        """自动收集"""
        ticket_no = self.workorder['ticket_no']
        if not ticket_no:
            QMessageBox.warning(self, "错误", "工单号为空")
            return

        dialog = CollectionDialog(ticket_no, self.db, self.config_loader, self)
        dialog.exec_()

        # 刷新数据
        self._load_screenshots()
        self._load_chat_messages()

    def _on_auto_fill(self):
        """自动录单"""
        # 检查是否有收集的数据
        screenshots = self.db.get_screenshots(self.ticket_id)
        messages = self.db.get_chat_messages(self.ticket_id)

        if not screenshots and not messages:
            QMessageBox.warning(self, "提示", "请先执行自动收集")
            return

        # 打开自动录单对话框
        dialog = AutoFillDialog(self.ticket_id, self.db, self.config_loader, self)
        dialog.exec_()

    def _on_save(self):
        """保存"""
        self.db.update_workorder(
            self.ticket_id,
            title=self.title_input.text(),
            priority=self.priority_combo.currentText(),
            problem_type=self.problem_type_combo.currentText(),
            host_ips=self.host_ip_input.text(),
            error_codes=self.error_code_input.text(),
            description=self.description_input.toPlainText()
        )

        # 更新 extracted_data
        extracted_data = {
            'title': self.title_input.text(),
            'priority': self.priority_combo.currentText(),
            'problem_type': self.problem_type_combo.currentText(),
            'host_ips': self.host_ip_input.text(),
            'error_codes': self.error_code_input.text(),
            'description': self.description_input.toPlainText()
        }
        self.db.update_extracted_data(self.ticket_id, extracted_data)

        QMessageBox.information(self, "成功", "保存成功")
