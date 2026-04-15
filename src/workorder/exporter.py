"""
数据导出模块
负责将提取的数据导出为不同格式
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class DataExporter:
    """数据导出器"""

    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(
        self, data: Dict[str, Any], ticket_no: str, prefix: str = "extract"
    ) -> str:
        """
        导出为 JSON 文件

        Args:
            data: 数据字典
            ticket_no: 工单号
            prefix: 文件名前缀

        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ticket_no}_{timestamp}.json"
        filepath = self.output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"数据已导出: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"导出 JSON 失败: {e}")
            raise

    def export_text(
        self, data: Dict[str, Any], ticket_no: str, prefix: str = "extract"
    ) -> str:
        """
        导出为文本文件

        Args:
            data: 数据字典
            ticket_no: 工单号
            prefix: 文件名前缀

        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ticket_no}_{timestamp}.txt"
        filepath = self.output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"工单号: {ticket_no}\n")
                f.write(f"提取时间: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")

                for key, value in data.items():
                    if isinstance(value, list):
                        f.write(f"{key}:\n")
                        for item in value:
                            f.write(f"  - {item}\n")
                    else:
                        f.write(f"{key}: {value}\n")

            logger.info(f"数据已导出: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"导出文本失败: {e}")
            raise

    def save_clipboard(self, text: str) -> None:
        """
        保存到剪贴板

        Args:
            text: 要复制的文本
        """
        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_TEXT)
            win32clipboard.CloseClipboard()

            logger.info("已复制到剪贴板")

        except ImportError:
            logger.warning("win32clipboard 未安装，无法复制到剪贴板")
        except Exception as e:
            logger.warning(f"复制到剪贴板失败: {e}")
