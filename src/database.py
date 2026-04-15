"""
数据库模块
使用 SQLite 存储工单信息
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class Database:
    """SQLite 数据库管理"""

    def __init__(self, db_path: str = "data/workorder.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 工单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workorders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no TEXT UNIQUE NOT NULL,
                title TEXT,
                status TEXT DEFAULT 'draft',
                priority TEXT,
                problem_type TEXT,
                description TEXT,
                host_ips TEXT,
                error_codes TEXT,
                extracted_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 收集的截图表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                sequence INTEGER DEFAULT 0,
                selected INTEGER DEFAULT 0,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES workorders(id)
            )
        """)

        # 聊天记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                sender TEXT,
                content TEXT,
                timestamp TEXT,
                selected INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES workorders(id)
            )
        """)

        conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def create_workorder(self, ticket_no: str, title: str = "", **kwargs) -> int:
        """
        创建工单

        Args:
            ticket_no: 工单号
            title: 标题
            **kwargs: 其他字段

        Returns:
            工单 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO workorders (ticket_no, title, **fields)
            VALUES (?, ?, ...)
        """.replace("**fields", ", ".join(f"`{k}`" for k in kwargs.keys())).replace("?," * len(kwargs), ", ".join(["?"] * len(kwargs))),

                       [ticket_no, title] + list(kwargs.values()))

        workorder_id = cursor.lastrowid
        conn.commit()
        logger.info(f"工单已创建: {ticket_no}, ID: {workorder_id}")
        return workorder_id

    def create_workorder_simple(self, ticket_no: str, title: str = "") -> int:
        """简化创建工单"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO workorders (ticket_no, title) VALUES (?, ?)",
            (ticket_no, title)
        )
        workorder_id = cursor.lastrowid
        conn.commit()
        return workorder_id

    def get_workorder(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """获取工单"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM workorders WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_workorder_by_ticket_no(self, ticket_no: str) -> Optional[Dict[str, Any]]:
        """通过工单号获取工单"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM workorders WHERE ticket_no = ?", (ticket_no,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_all_workorders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有工单"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT * FROM workorders WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM workorders ORDER BY created_at DESC")

        return [dict(row) for row in cursor.fetchall()]

    def update_workorder(self, ticket_id: int, **kwargs) -> None:
        """更新工单"""
        if not kwargs:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        set_clause = ", ".join(f"`{k}` = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [ticket_id]

        cursor.execute(f"UPDATE workorders SET {set_clause}, updated_at = ? WHERE id = ?",
                      values + [datetime.now().isoformat(), ticket_id])
        conn.commit()
        logger.debug(f"工单已更新: ID={ticket_id}")

    def update_extracted_data(self, ticket_id: int, data: Dict[str, Any]) -> None:
        """更新提取的数据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE workorders SET extracted_data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(data, ensure_ascii=False), datetime.now().isoformat(), ticket_id)
        )
        conn.commit()

    def delete_workorder(self, ticket_id: int) -> None:
        """删除工单"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM chat_messages WHERE ticket_id = ?", (ticket_id,))
        cursor.execute("DELETE FROM screenshots WHERE ticket_id = ?", (ticket_id,))
        cursor.execute("DELETE FROM workorders WHERE id = ?", (ticket_id,))
        conn.commit()

    # ===== 截图管理 =====

    def add_screenshot(self, ticket_id: int, file_path: str, sequence: int = 0) -> int:
        """添加截图"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO screenshots (ticket_id, file_path, sequence) VALUES (?, ?, ?)",
            (ticket_id, file_path, sequence)
        )
        screenshot_id = cursor.lastrowid
        conn.commit()
        return screenshot_id

    def get_screenshots(self, ticket_id: int) -> List[Dict[str, Any]]:
        """获取工单的所有截图"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM screenshots WHERE ticket_id = ? ORDER BY sequence",
            (ticket_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_screenshot_selection(self, screenshot_id: int, selected: bool, note: str = "") -> None:
        """更新截图选择状态"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE screenshots SET selected = ?, note = ? WHERE id = ?",
            (1 if selected else 0, note, screenshot_id)
        )
        conn.commit()

    def get_selected_screenshots(self, ticket_id: int) -> List[Dict[str, Any]]:
        """获取选中的截图"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM screenshots WHERE ticket_id = ? AND selected = 1 ORDER BY sequence",
            (ticket_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== 聊天记录管理 =====

    def add_chat_message(self, ticket_id: int, sender: str, content: str, timestamp: str = "") -> int:
        """添加聊天记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO chat_messages (ticket_id, sender, content, timestamp) VALUES (?, ?, ?, ?)",
            (ticket_id, sender, content, timestamp)
        )
        message_id = cursor.lastrowid
        conn.commit()
        return message_id

    def get_chat_messages(self, ticket_id: int) -> List[Dict[str, Any]]:
        """获取工单的所有聊天记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM chat_messages WHERE ticket_id = ? ORDER BY id",
            (ticket_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_message_selection(self, message_id: int, selected: bool) -> None:
        """更新消息选择状态"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE chat_messages SET selected = ? WHERE id = ?",
            (1 if selected else 0, message_id)
        )
        conn.commit()

    def get_selected_messages(self, ticket_id: int) -> List[Dict[str, Any]]:
        """获取选中的消息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM chat_messages WHERE ticket_id = ? AND selected = 1 ORDER BY id",
            (ticket_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
