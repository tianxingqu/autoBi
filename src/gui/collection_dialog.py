"""
自动收集对话框
显示 Welink 截图和聊天记录，供用户挑选
"""

import os
import time
from pathlib import Path
from typing import List, Optional

from loguru import logger
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QCheckBox,
    QProgressBar, QMessageBox, QScrollArea, QWidget, QGridLayout,
    QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

from ..database import Database
from ..core.keyword_matcher import KeywordMatcher, MatchResult
from ..core.config_loader import ConfigLoader
from ..welink.collector import WelinkCollector


class CollectionWorker(QThread):
    """收集工作线程"""

    progress = pyqtSignal(int, str)  # progress, message
    screenshots_ready = pyqtSignal(list)  # list of screenshot paths
    messages_ready = pyqtSignal(list)  # list of message dicts
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, ticket_no: str, collector: WelinkCollector, keyword_matcher: KeywordMatcher):
        super().__init__()
        self.ticket_no = ticket_no
        self.collector = collector
        self.keyword_matcher = keyword_matcher

    def run(self):
        """执行收集"""
        try:
            # Step 1: 连接 Welink
            self.progress.emit(10, "正在连接 Welink...")
            self.collector.connect()
            self.progress.emit(20, "Welink 连接成功")

            # Step 2: 搜索群
            self.progress.emit(30, f"正在搜索群: {self.ticket_no}...")
            if not self.collector.search_group(self.ticket_no):
                self.error.emit(f"未找到工单群: {self.ticket_no}")
                return
            self.progress.emit(40, "群搜索成功")

            # Step 3: 截图
            self.progress.emit(50, "正在截图...")
            screenshots = self.collector.take_screenshots(count=10)
            self.screenshots_ready.emit(screenshots)
            self.progress.emit(70, f"截图完成 ({len(screenshots)} 张)")

            # Step 4: 读取消息
            self.progress.emit(80, "正在读取聊天记录...")
            messages = self.collector.get_messages(count=50)
            self.messages_ready.emit(messages)
            self.progress.emit(90, f"读取消息完成 ({len(messages)} 条)")

            # Step 5: 关键字匹配
            self.progress.emit(95, "正在进行关键字匹配...")
            message_dicts = [{'content': m.content} for m in messages]
            match_results = self.keyword_matcher.match_all(message_dicts)
            merged = self.keyword_matcher.merge_results(match_results)
            self.progress.emit(100, "收集完成")
            self.finished.emit()

            logger.info(f"收集完成: {len(screenshots)} 张截图, {len(messages)} 条消息")

        except Exception as e:
            logger.exception(f"收集失败: {e}")
            self.error.emit(str(e))


class ScreenshotViewer(QScrollArea):
    """截图查看器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumHeight(300)

        self.container = QWidget()
        self.layout = QGridLayout()
        self.container.setLayout(self.layout)
        self.setWidget(self.container)

        self.screenshot_labels = []
        self.checkboxes = []

    def load_screenshots(self, screenshot_paths: List[str]):
        """加载截图"""
        # 清除旧数据
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.screenshot_labels.clear()
        self.checkboxes.clear()

        # 2列布局
        for i, path in enumerate(screenshot_paths):
            row = i // 2
            col = i % 2

            # 复选框
            checkbox = QCheckBox(f"选择截图 {i+1}")
            checkbox.setChecked(True)
            self.checkboxes.append((checkbox, path))

            # 截图标签
            label = QLabel()
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # 缩放图片
                scaled = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(scaled)
            else:
                label.setText("图片加载失败")

            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("border: 1px solid #ccc; padding: 5px;")

            # 添加到布局
            self.layout.addWidget(checkbox, row * 2, col, 1, 1)
            self.layout.addWidget(label, row * 2 + 1, col, 1, 1)

    def get_selected_paths(self) -> List[str]:
        """获取选中的截图路径"""
        return [path for cb, path in self.checkboxes if cb.isChecked()]


class MessageList(QListWidget):
    """消息列表"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message_items = []

    def load_messages(self, messages: List[dict]):
        """加载消息"""
        self.clear()
        self.message_items.clear()

        for msg in messages:
            item = QListWidgetItem()
            content = msg.get('content', '')
            sender = msg.get('sender', '')
            text = f"{sender}: {content[:80]}{'...' if len(content) > 80 else ''}"

            item.setText(text)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, msg)
            self.addItem(item)
            self.message_items.append((item, msg))

    def get_selected_messages(self) -> List[dict]:
        """获取选中的消息"""
        selected = []
        for i in range(self.count()):
            item = self.item(i)
            if item.checkState() == Qt.Checked:
                msg = item.data(Qt.UserRole)
                selected.append(msg)
        return selected


class CollectionDialog(QDialog):
    """自动收集对话框"""

    def __init__(self, ticket_no: str, db: Database, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.ticket_no = ticket_no
        self.db = db
        self.config_loader = config_loader
        self.keyword_matcher = KeywordMatcher(config_loader)

        self.collector = WelinkCollector(config_loader)
        self.worker: Optional[CollectionWorker] = None

        self.screenshot_paths: List[str] = []
        self.messages: List[dict] = []
        self.match_result: Optional[MatchResult] = None

        self.setWindowTitle(f"自动收集 - {ticket_no}")
        self.setModal(True)
        self.setGeometry(200, 200, 800, 900)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("准备就绪")
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        # 开始收集按钮
        self.btn_start = QPushButton("开始收集")
        self.btn_start.clicked.connect(self._on_start_collect)
        layout.addWidget(self.btn_start)

        # 截图查看器
        screenshot_group = QGroupBox("截图 (勾选表示选择)")
        screenshot_layout = QVBoxLayout()
        screenshot_group.setLayout(screenshot_layout)
        self.screenshot_viewer = ScreenshotViewer()
        screenshot_layout.addWidget(self.screenshot_viewer)
        layout.addWidget(screenshot_group)

        # 聊天记录
        message_group = QGroupBox("聊天记录 (勾选表示选择)")
        message_layout = QVBoxLayout()
        message_group.setLayout(message_layout)
        self.message_list = MessageList()
        message_layout.addWidget(self.message_list)
        layout.addWidget(message_group)

        # 提取结果
        result_group = QGroupBox("关键字提取结果")
        result_layout = QVBoxLayout()
        result_group.setLayout(result_layout)
        self.result_label = QLabel("暂无数据")
        self.result_label.setWordWrap(True)
        result_layout.addWidget(self.result_label)
        layout.addWidget(result_group)

        # 按钮
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_save = QPushButton("保存选择")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setEnabled(False)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)

    def _on_start_collect(self):
        """开始收集"""
        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在连接 Welink...")

        self.worker = CollectionWorker(
            self.ticket_no,
            self.collector,
            self.keyword_matcher
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.screenshots_ready.connect(self._on_screenshots_ready)
        self.worker.messages_ready.connect(self._on_messages_ready)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def _on_screenshots_ready(self, paths: List[str]):
        """截图就绪"""
        self.screenshot_paths = paths
        self.screenshot_viewer.load_screenshots(paths)

    def _on_messages_ready(self, messages: List[dict]):
        """消息就绪"""
        self.messages = messages
        self.message_list.load_messages(messages)

    def _on_finished(self):
        """收集完成"""
        # 关键字匹配
        message_dicts = [{'content': m['content']} for m in self.messages]
        results = self.keyword_matcher.match_all(message_dicts)
        self.match_result = self.keyword_matcher.merge_results(results)

        # 显示结果
        result_text = f"问题类型: {self.match_result.problem_type or '未识别'}\n"
        result_text += f"优先级: {self.match_result.priority or '未识别'}\n"
        result_text += f"服务器IP: {', '.join(self.match_result.host_ips) if self.match_result.host_ips else '未识别'}\n"
        result_text += f"错误码: {', '.join(self.match_result.error_codes) if self.match_result.error_codes else '未识别'}"
        self.result_label.setText(result_text)

        self.btn_save.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.progress_label.setText("收集完成，请挑选要保存的内容")

    def _on_error(self, error_msg: str):
        """错误处理"""
        QMessageBox.critical(self, "错误", f"收集失败:\n{error_msg}")
        self.btn_start.setEnabled(True)

    def _on_save(self):
        """保存选择"""
        try:
            # 保存选中的截图
            selected_screenshots = self.screenshot_viewer.get_selected_paths()
            for i, path in enumerate(selected_screenshots):
                self.db.add_screenshot(self.ticket_id, path, i)

            # 保存选中的消息
            selected_messages = self.message_list.get_selected_messages()
            for msg in selected_messages:
                self.db.add_chat_message(
                    self.ticket_id,
                    msg.get('sender', ''),
                    msg.get('content', ''),
                    msg.get('timestamp', '')
                )

            # 更新工单提取数据
            if self.match_result:
                extracted_data = {
                    'problem_type': self.match_result.problem_type,
                    'priority': self.match_result.priority,
                    'host_ips': self.match_result.host_ips,
                    'error_codes': self.match_result.error_codes,
                    'ticket_refs': self.match_result.ticket_refs,
                }
                self.db.update_extracted_data(self.ticket_id, extracted_data)
                self.db.update_workorder(
                    self.ticket_id,
                    priority=self.match_result.priority,
                    problem_type=self.match_result.problem_type,
                    host_ips=', '.join(self.match_result.host_ips) if self.match_result.host_ips else '',
                    error_codes=', '.join(self.match_result.error_codes) if self.match_result.error_codes else ''
                )

            # 更新状态
            self.db.update_workorder(self.ticket_id, status='ready')

            QMessageBox.information(self, "成功",
                f"已保存:\n- {len(selected_screenshots)} 张截图\n- {len(selected_messages)} 条消息")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")

    def closeEvent(self, event):
        """关闭时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        try:
            self.collector.close()
        except Exception:
            pass
        event.accept()
