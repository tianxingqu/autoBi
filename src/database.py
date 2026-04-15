"""
数据库模块
使用 SQLite 存储工单信息
支持配置文件定义表结构
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .core.config_loader import ConfigLoader
from .core.exceptions import ConfigLoadError


class Database:
    """SQLite 数据库管理"""

    def __init__(self, db_path: str = "data/workorder.db", config_loader: Optional[ConfigLoader] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

        # 加载表结构配置
        self.config_loader = config_loader or ConfigLoader()
        self._load_schema()

        # 初始化数据库
        self._init_db()

    def _load_schema(self) -> None:
        """加载表结构配置"""
        try:
            self.schema = self.config_loader.load("db-schema")
        except ConfigLoadError as e:
            logger.warning(f"无法加载数据库配置，使用默认配置: {e}")
            self.schema = self._get_default_schema()

    def _get_default_schema(self) -> Dict[str, Any]:
        """获取默认表结构"""
        return {
            "tables": {
                "workorders": {
                    "table_name": "workorders",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True, "nullable": False},
                        {"name": "ticket_no", "type": "TEXT", "unique": True, "nullable": False},
                        {"name": "status", "type": "TEXT", "default": "draft"},
                        {"name": "priority", "type": "TEXT"},
                        {"name": "problem_type", "type": "TEXT"},
                        {"name": "title", "type": "TEXT"},
                        {"name": "description", "type": "TEXT"},
                        {"name": "host_ips", "type": "TEXT"},
                        {"name": "error_codes", "type": "TEXT"},
                        {"name": "extracted_data", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT", "default": "CURRENT_TIMESTAMP"},
                        {"name": "updated_at", "type": "TEXT", "default": "CURRENT_TIMESTAMP"},
                    ]
                },
                "screenshots": {
                    "table_name": "screenshots",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True},
                        {"name": "ticket_id", "type": "INTEGER", "nullable": False, "foreign_key": "workorders(id)"},
                        {"name": "file_path", "type": "TEXT", "nullable": False},
                        {"name": "sequence", "type": "INTEGER", "default": 0},
                        {"name": "selected", "type": "INTEGER", "default": 0},
                        {"name": "note", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT", "default": "CURRENT_TIMESTAMP"},
                    ]
                },
                "chat_messages": {
                    "table_name": "chat_messages",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True},
                        {"name": "ticket_id", "type": "INTEGER", "nullable": False, "foreign_key": "workorders(id)"},
                        {"name": "sender", "type": "TEXT"},
                        {"name": "content", "type": "TEXT"},
                        {"name": "timestamp", "type": "TEXT"},
                        {"name": "selected", "type": "INTEGER", "default": 0},
                        {"name": "created_at", "type": "TEXT", "default": "CURRENT_TIMESTAMP"},
                    ]
                },
                "attachments": {
                    "table_name": "attachments",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True},
                        {"name": "ticket_id", "type": "INTEGER", "nullable": False, "foreign_key": "workorders(id)"},
                        {"name": "file_path", "type": "TEXT", "nullable": False},
                        {"name": "file_name", "type": "TEXT"},
                        {"name": "file_type", "type": "TEXT"},
                        {"name": "file_size", "type": "INTEGER"},
                        {"name": "selected", "type": "INTEGER", "default": 0},
                        {"name": "note", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT", "default": "CURRENT_TIMESTAMP"},
                    ]
                },
                "workorder_ext": {
                    "table_name": "workorder_ext",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True},
                        {"name": "ticket_id", "type": "INTEGER", "nullable": False, "foreign_key": "workorders(id)"},
                        {"name": "field_name", "type": "TEXT", "nullable": False},
                        {"name": "field_value", "type": "TEXT"},
                        {"name": "field_type", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT", "default": "CURRENT_TIMESTAMP"},
                    ]
                },
            }
        }

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _build_column_def(self, column: Dict[str, Any]) -> str:
        """构建列定义 SQL"""
        col_def = f"{column['name']} {column['type']}"

        if column.get('primary_key'):
            col_def += " PRIMARY KEY"
            if column.get('autoincrement'):
                col_def += " AUTOINCREMENT"
        if column.get('unique'):
            col_def += " UNIQUE"
        if not column.get('nullable', True) and not column.get('primary_key'):
            col_def += " NOT NULL"
        if column.get('default'):
            default = column['default']
            if default == "CURRENT_TIMESTAMP":
                col_def += " DEFAULT CURRENT_TIMESTAMP"
            else:
                col_def += f" DEFAULT '{default}'"

        return col_def

    def _build_foreign_key_def(self, column: Dict[str, Any]) -> Optional[str]:
        """构建外键定义"""
        if column.get('foreign_key'):
            return f"FOREIGN KEY ({column['name']}) REFERENCES {column['foreign_key']}"
        return None

    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        tables = self.schema.get("tables", {})

        for table_key, table_config in tables.items():
            table_name = table_config.get("table_name", table_key)
            columns = table_config.get("columns", [])

            # 构建 CREATE TABLE 语句
            column_defs = []
            foreign_keys = []

            for col in columns:
                column_defs.append(self._build_column_def(col))

                fk_def = self._build_foreign_key_def(col)
                if fk_def:
                    foreign_keys.append(fk_def)

            column_defs.extend(foreign_keys)

            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"

            try:
                cursor.execute(create_sql)
                logger.debug(f"表 {table_name} 已创建或已存在")
            except sqlite3.Error as e:
                logger.error(f"创建表 {table_name} 失败: {e}")

        conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def _get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有列名"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    # ===== 工单管理 =====

    def create_workorder(self, ticket_no: str, title: str = "", **kwargs) -> int:
        """创建工单"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 获取表结构
        columns = self._get_table_columns("workorders")

        # 过滤有效的列
        valid_kwargs = {k: v for k, v in kwargs.items() if k in columns}

        if valid_kwargs:
            cols = ", ".join(valid_kwargs.keys())
            placeholders = ", ".join(["?"] * len(valid_kwargs))
            values = list(valid_kwargs.values())

            cursor.execute(
                f"INSERT INTO workorders (ticket_no, title, {cols}) VALUES (?, ?, {placeholders})",
                [ticket_no, title] + values
            )
        else:
            cursor.execute(
                "INSERT INTO workorders (ticket_no, title) VALUES (?, ?)",
                (ticket_no, title)
            )

        workorder_id = cursor.lastrowid
        conn.commit()
        logger.info(f"工单已创建: {ticket_no}, ID: {workorder_id}")
        return workorder_id

    def create_workorder_simple(self, ticket_no: str, title: str = "") -> int:
        """简化创建工单"""
        return self.create_workorder(ticket_no, title)

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

        # 获取表结构
        columns = self._get_table_columns("workorders")

        # 过滤有效的列
        valid_kwargs = {k: v for k, v in kwargs.items() if k in columns}

        if not valid_kwargs:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        set_clause = ", ".join(f"{k} = ?" for k in valid_kwargs.keys())
        values = list(valid_kwargs.values()) + [datetime.now().isoformat(), ticket_id]

        cursor.execute(
            f"UPDATE workorders SET {set_clause}, updated_at = ? WHERE id = ?",
            values
        )
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

        # 删除关联数据
        cursor.execute("DELETE FROM chat_messages WHERE ticket_id = ?", (ticket_id,))
        cursor.execute("DELETE FROM screenshots WHERE ticket_id = ?", (ticket_id,))
        cursor.execute("DELETE FROM attachments WHERE ticket_id = ?", (ticket_id,))
        cursor.execute("DELETE FROM workorder_ext WHERE ticket_id = ?", (ticket_id,))
        cursor.execute("DELETE FROM workorders WHERE id = ?", (ticket_id,))
        conn.commit()

    # ===== 扩展字段 =====

    def set_ext_field(self, ticket_id: int, field_name: str, field_value: str, field_type: str = "text") -> None:
        """设置扩展字段"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO workorder_ext (ticket_id, field_name, field_value, field_type)
            VALUES (?, ?, ?, ?)
        """, (ticket_id, field_name, field_value, field_type))
        conn.commit()

    def get_ext_fields(self, ticket_id: int) -> Dict[str, str]:
        """获取工单的所有扩展字段"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT field_name, field_value, field_type FROM workorder_ext WHERE ticket_id = ?",
            (ticket_id,)
        )

        result = {}
        for row in cursor.fetchall():
            result[row[0]] = {"value": row[1], "type": row[2]}
        return result

    def delete_ext_field(self, ticket_id: int, field_name: str) -> None:
        """删除扩展字段"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM workorder_ext WHERE ticket_id = ? AND field_name = ?",
            (ticket_id, field_name)
        )
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

    # ===== 附件管理 =====

    def add_attachment(self, ticket_id: int, file_path: str, file_name: str = "",
                       file_type: str = "", file_size: int = 0) -> int:
        """添加附件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO attachments (ticket_id, file_path, file_name, file_type, file_size)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_id, file_path, file_name, file_type, file_size))

        attachment_id = cursor.lastrowid
        conn.commit()
        return attachment_id

    def get_attachments(self, ticket_id: int) -> List[Dict[str, Any]]:
        """获取工单的所有附件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM attachments WHERE ticket_id = ? ORDER BY id",
            (ticket_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== 工具方法 =====

    def get_schema(self) -> Dict[str, Any]:
        """获取当前表结构配置"""
        return self.schema

    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        return list(self.schema.get("tables", {}).keys())

    def get_table_columns(self, table_key: str) -> List[Dict[str, Any]]:
        """获取表的列配置"""
        table_config = self.schema.get("tables", {}).get(table_key, {})
        return table_config.get("columns", [])

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
