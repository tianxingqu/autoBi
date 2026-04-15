"""
自动录单对话框
从收集的信息自动填入工单系统
"""

import asyncio
import json
from typing import Optional

from loguru import logger
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QMessageBox,
    QGroupBox, QCheckBox, QLineEdit
)
from PyQt5.QtCore import QThread, pyqtSignal

from ..database import Database
from ..core.config_loader import ConfigLoader
from ..workorder.filler import TicketSystemFiller


class FillWorker(QThread):
    """录单工作线程"""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, filler: TicketSystemFiller, extracted_data: dict):
        super().__init__()
        self.filler = filler
        self.extracted_data = extracted_data

    def run(self):
        """执行录单"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def do_fill():
                # Step 1: 打开工单系统
                self.progress.emit(10, "打开工单系统...")
                await self.filler.open()

                # Step 2: 填充表单
                self.progress.emit(30, "填充表单...")
                await self.filler.fill_all(self.extracted_data)

                # Step 3: 截图确认
                self.progress.emit(80, "截图确认...")
                await self.filler.take_screenshot("data/screenshots/filled_form.png")

                # Step 4: 完成
                self.progress.emit(100, "录单完成")
                await self.filler.close()

            loop.run_until_complete(do_fill())
            loop.close()

            self.finished.emit(True, "录单完成")
            logger.info("自动录单完成")

        except Exception as e:
            logger.exception(f"录单失败: {e}")
            self.error.emit(str(e))


class AutoFillDialog(QDialog):
    """自动录单对话框"""

    def __init__(self, ticket_id: int, db: Database, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.db = db
        self.config_loader = config_loader
        self.workorder = db.get_workorder(ticket_id)

        self.filler: Optional[TicketSystemFiller] = None
        self.worker: Optional[FillWorker] = None

        self.setWindowTitle(f"自动录单 - {self.workorder['ticket_no']}")
        self.setModal(True)
        self.setGeometry(250, 250, 600, 500)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 工单号
        row = QHBoxLayout()
        layout.addLayout(row)
        row.addWidget(QLabel("工单号:"))
        self.ticket_no_label = QLabel()
        row.addWidget(self.ticket_no_label)
        row.addStretch()

        # 提取的数据预览
        data_group = QGroupBox("提取的数据 (将填入工单系统)")
        data_layout = QVBoxLayout()
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        self.data_preview = QTextEdit()
        self.data_preview.setReadOnly(True)
        self.data_preview.setMaximumHeight(200)
        data_layout.addWidget(self.data_preview)

        # 字段映射预览
        mapping_group = QGroupBox("字段映射预览")
        mapping_layout = QVBoxLayout()
        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)

        self.mapping_preview = QTextEdit()
        self.mapping_preview.setReadOnly(True)
        self.mapping_preview.setMaximumHeight(150)
        mapping_layout.addWidget(self.mapping_preview)

        # 进度
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_start = QPushButton("开始自动录单")
        self.btn_start.clicked.connect(self._on_start_fill)
        btn_layout.addWidget(self.btn_start)

        self.btn_close = QPushButton("取消")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

    def _load_data(self):
        """加载数据"""
        wo = self.workorder
        if not wo:
            return

        self.ticket_no_label.setText(wo['ticket_no'] or '')

        # 显示提取的数据
        extracted_data = wo.get('extracted_data', '')
        if extracted_data:
            if isinstance(extracted_data, str):
                try:
                    extracted_data = json.loads(extracted_data)
                except:
                    pass

            preview = []
            for key, value in extracted_data.items():
                if value:
                    if isinstance(value, list):
                        preview.append(f"{key}: {', '.join(str(v) for v in value)}")
                    else:
                        preview.append(f"{key}: {value}")
            self.data_preview.setText("\n".join(preview) if preview else "无数据")
        else:
            self.data_preview.setText("无数据")

        # 显示字段映射
        field_config = self.config_loader.load_field_mapping()
        fields = field_config.get('ticket_system', {}).get('fields', [])
        mapping_text = []
        for field in fields:
            name = field.get('name', '')
            selector = field.get('selector', '')
            mapping_text.append(f"{name} -> {selector}")
        self.mapping_preview.setText("\n".join(mapping_text) if mapping_text else "无映射")

    def _on_start_fill(self):
        """开始自动录单"""
        # 获取提取的数据
        extracted_data = self.workorder.get('extracted_data', '')
        if extracted_data:
            if isinstance(extracted_data, str):
                try:
                    extracted_data = json.loads(extracted_data)
                except:
                    extracted_data = {}
        else:
            extracted_data = {}

        if not extracted_data:
            QMessageBox.warning(self, "提示", "没有可用的提取数据，请先执行自动收集")
            return

        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("准备开始...")

        # 初始化填充器
        self.filler = TicketSystemFiller(self.config_loader)

        # 开始工作线程
        self.worker = FillWorker(self.filler, extracted_data)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def _on_finished(self, success: bool, message: str):
        """完成"""
        self.btn_start.setEnabled(True)

        if success:
            # 更新工单状态
            self.db.update_workorder(self.ticket_id, status='submitted')
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "提示", message)

    def _on_error(self, error_msg: str):
        """错误"""
        self.btn_start.setEnabled(True)
        QMessageBox.critical(self, "错误", f"录单失败:\n{error_msg}")

    def closeEvent(self, event):
        """关闭"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()
