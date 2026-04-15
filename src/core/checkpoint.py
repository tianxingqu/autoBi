"""
断点管理模块
支持运行状态的保存和恢复
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .exceptions import CheckpointError


class Checkpoint:
    """断点管理"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, ticket_no: str) -> Path:
        """获取断点文件路径"""
        # 清理工单号中的非法字符
        safe_ticket_no = "".join(c if c.isalnum() else "_" for c in ticket_no)
        return self.checkpoint_dir / f"checkpoint_{safe_ticket_no}.json"

    def save(
        self,
        ticket_no: str,
        stage: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        保存断点

        Args:
            ticket_no: 工单号
            stage: 当前阶段
            data: 断点数据
            metadata: 元数据（时间戳等）
        """
        checkpoint_path = self._get_checkpoint_path(ticket_no)

        checkpoint_data = {
            "ticket_no": ticket_no,
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metadata": metadata or {}
        }

        try:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"断点已保存: {stage} -> {checkpoint_path}")
        except Exception as e:
            logger.warning(f"断点保存失败: {e}")
            raise CheckpointError(f"断点保存失败: {e}")

    def load(self, ticket_no: str) -> Optional[Dict[str, Any]]:
        """
        加载断点

        Args:
            ticket_no: 工单号

        Returns:
            断点数据，如果不存在返回 None
        """
        checkpoint_path = self._get_checkpoint_path(ticket_no)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
            logger.info(f"断点已加载: {checkpoint_data.get('stage')} @ {checkpoint_data.get('timestamp')}")
            return checkpoint_data
        except Exception as e:
            logger.warning(f"断点加载失败: {e}")
            return None

    def delete(self, ticket_no: str) -> None:
        """删除断点"""
        checkpoint_path = self._get_checkpoint_path(ticket_no)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.debug(f"断点已删除: {checkpoint_path}")

    def exists(self, ticket_no: str) -> bool:
        """检查断点是否存在"""
        return self._get_checkpoint_path(ticket_no).exists()

    def list_checkpoints(self) -> list:
        """列出所有断点"""
        return [
            f.stem.replace("checkpoint_", "")
            for f in self.checkpoint_dir.glob("checkpoint_*.json")
        ]


class CheckpointStage:
    """断点阶段常量"""

    WELINK_CONNECTED = "welink_connected"
    GROUP_ENTERED = "group_entered"
    MESSAGES_EXTRACTED = "messages_extracted"
    READY_TO_FILL = "ready_to_fill"
