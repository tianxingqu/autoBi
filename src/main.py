#!/usr/bin/env python3
"""
运维工单录入自动化框架
入口文件

功能：
1. 在 Welink 中搜索工单群
2. 读取群消息并匹配关键字
3. 将提取的信息自动填入工单系统

用法：
    python main.py --ticket-no ITSM-2024-00123
    python main.py --ticket-no ITSM-2024-00123 --extract-only
    python main.py --ticket-no ITSM-2024-00123 --debug
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

from src.core.config_loader import ConfigLoader
from src.core.checkpoint import Checkpoint, CheckpointStage
from src.core.keyword_matcher import KeywordMatcher, MatchResult
from src.core.logger import setup_logger
from src.core.exceptions import WorkOrderError

from src.welink.connector import WelinkConnector
from src.welink.search import WelinkSearch
from src.welink.chat import WelinkChat, Message

from src.workorder.filler import TicketSystemFiller
from src.workorder.exporter import DataExporter


class WorkOrderAutomation:
    """工单自动化主流程"""

    def __init__(self, config_dir: str = "config"):
        self.config_loader = ConfigLoader(config_dir)
        self.settings = self.config_loader.load_settings()

        # 初始化组件
        self.keyword_matcher = KeywordMatcher(self.config_loader)
        self.checkpoint = Checkpoint(
            self.settings.get("checkpoint", {}).get("directory", "checkpoints")
        )
        self.exporter = DataExporter()

        # Welink 组件
        self.connector: Optional[WelinkConnector] = None
        self.search: Optional[WelinkSearch] = None
        self.chat: Optional[WelinkChat] = None

        # 工单系统组件
        self.filler: Optional[TicketSystemFiller] = None

        # 提取结果
        self.last_result: Optional[MatchResult] = None

    def _setup_logging(self, debug: bool = False) -> None:
        """设置日志"""
        log_config = self.settings.get("logging", {})
        setup_logger(
            level="DEBUG" if debug else log_config.get("level", "INFO"),
            log_dir=log_config.get("log_dir", "logs"),
            rotation=log_config.get("rotation", "00:00"),
            retention=log_config.get("retention", "7 days"),
            save_to_file=log_config.get("save_to_file", True)
        )

    async def run(
        self,
        ticket_no: str,
        extract_only: bool = False,
        auto_fill: bool = True,
        auto_confirm: bool = False,
        debug: bool = False
    ) -> MatchResult:
        """
        运行自动化流程

        Args:
            ticket_no: 工单号
            extract_only: 是否仅提取（不填工单系统）
            auto_fill: 是否自动填充工单系统
            auto_confirm: 是否自动确认（跳过确认步骤）
            debug: 调试模式

        Returns:
            MatchResult: 匹配结果
        """
        self._setup_logging(debug)
        logger.info(f"=" * 60)
        logger.info(f"工单自动化流程启动 - 工单号: {ticket_no}")
        logger.info(f"=" * 60)

        try:
            # Step 1: 连接 Welink
            await self._step_connect_welink(ticket_no)

            # Step 2: 搜索工单群
            await self._step_search_group(ticket_no)

            # Step 3: 读取群消息
            messages = await self._step_read_messages(ticket_no)

            # Step 4: 关键字匹配
            result = await self._step_keyword_matching(messages, ticket_no)

            # Step 5: 显示结果并等待确认
            self._show_result(result, ticket_no)

            if not auto_confirm:
                confirm = input("\n确认是否继续填充工单系统? (y/n): ").strip().lower()
                if confirm != 'y':
                    logger.info("用户取消，流程结束")
                    return result

            # Step 6: 填充工单系统
            if not extract_only and auto_fill:
                await self._step_fill_workorder(result, ticket_no)

            logger.info("流程完成!")
            return result

        except WorkOrderError as e:
            logger.error(f"流程执行失败: {e}")
            raise

        except Exception as e:
            logger.exception(f"未预期的错误: {e}")
            raise

        finally:
            # 保存检查点
            if self.connector and self.connector.is_connected():
                try:
                    self.connector.close()
                except Exception:
                    pass

    async def _step_connect_welink(self, ticket_no: str) -> None:
        """Step 1: 连接 Welink"""
        logger.info("[Step 1/6] 连接 Welink...")

        self.connector = WelinkConnector(self.config_loader)
        self.connector.connect()

        self.search = WelinkSearch(self.connector)
        self.chat = WelinkChat(self.connector, self.config_loader)

        logger.info("Welink 连接成功")

    async def _step_search_group(self, ticket_no: str) -> None:
        """Step 2: 搜索工单群"""
        logger.info(f"[Step 2/6] 搜索工单群: {ticket_no}...")

        if not self.search:
            raise WorkOrderError("Welink 未连接")

        success = self.search.search_group(ticket_no)
        if not success:
            raise WorkOrderError(f"未找到工单群: {ticket_no}")

        logger.info("工单群搜索成功")

    async def _step_read_messages(self, ticket_no: str) -> list:
        """Step 3: 读取群消息"""
        logger.info("[Step 3/6] 读取群消息...")

        if not self.chat:
            raise WorkOrderError("Welink 未连接")

        messages = self.chat.get_messages(count=100)

        if not messages:
            logger.warning("未读取到任何消息")

        logger.info(f"成功读取 {len(messages)} 条消息")
        return messages

    async def _step_keyword_matching(self, messages: list, ticket_no: str) -> MatchResult:
        """Step 4: 关键字匹配"""
        logger.info("[Step 4/6] 关键字匹配...")

        # 提取消息内容
        message_dicts = self.chat.extract_content(messages)

        # 批量匹配
        results = self.keyword_matcher.match_all(message_dicts)

        # 合并结果
        merged = self.keyword_matcher.merge_results(results)

        self.last_result = merged

        logger.info(f"匹配完成: {merged}")

        return merged

    def _show_result(self, result: MatchResult, ticket_no: str) -> None:
        """显示匹配结果"""
        logger.info("\n" + "=" * 50)
        logger.info(f"提取结果 - 工单号: {ticket_no}")
        logger.info("=" * 50)
        logger.info(str(result))
        logger.info("=" * 50 + "\n")

        # 导出数据
        try:
            filepath = self.exporter.export_json(result.to_dict(), ticket_no, prefix="extract")
            logger.info(f"提取结果已保存: {filepath}")
        except Exception as e:
            logger.warning(f"导出失败: {e}")

    async def _step_fill_workorder(self, result: MatchResult, ticket_no: str) -> None:
        """Step 5-6: 填充工单系统"""
        logger.info("[Step 5/6] 打开工单系统...")

        self.filler = TicketSystemFiller(self.config_loader)
        await self.filler.open()

        logger.info("[Step 6/6] 填充工单表单...")

        # 将匹配结果转换为字典格式
        data = {
            "problem_type": result.problem_type,
            "priority": result.priority,
            "host_ips": ", ".join(result.host_ips) if result.host_ips else "",
            "ticket_refs": ", ".join(result.ticket_refs) if result.ticket_refs else "",
            "error_codes": ", ".join(result.error_codes) if result.error_codes else "",
            "description": result.raw_matches.get("description", [""])[0] if result.raw_matches.get("description") else "",
        }

        await self.filler.fill_all(data)

        # 询问是否提交
        submit = input("是否提交工单? (y/n): ").strip().lower()
        if submit == 'y':
            await self.filler.submit()

        await self.filler.close()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="运维工单录入自动化框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --ticket-no ITSM-2024-00123
  python main.py --ticket-no ITSM-2024-00123 --extract-only
  python main.py --ticket-no ITSM-2024-00123 --debug
        """
    )

    parser.add_argument(
        "--ticket-no",
        required=True,
        help="工单号"
    )

    parser.add_argument(
        "--config",
        default="config",
        help="配置文件目录 (默认: config)"
    )

    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="仅提取信息，不填工单系统"
    )

    parser.add_argument(
        "--auto-fill",
        action="store_true",
        default=True,
        help="自动填充工单系统 (默认: True)"
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help="跳过所有确认步骤"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    try:
        automation = WorkOrderAutomation(config_dir=args.config)

        result = asyncio.run(
            automation.run(
                ticket_no=args.ticket_no,
                extract_only=args.extract_only,
                auto_fill=args.auto_fill,
                auto_confirm=args.yes,
                debug=args.debug
            )
        )

        print("\n最终结果:")
        print(result)

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(130)

    except WorkOrderError as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
