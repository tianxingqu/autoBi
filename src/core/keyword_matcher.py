"""
关键字匹配引擎
从消息内容中提取关键信息
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .config_loader import ConfigLoader


@dataclass
class MatchResult:
    """匹配结果"""

    problem_type: Optional[str] = None  # 问题类型
    priority: Optional[str] = None  # 优先级
    host_ips: List[str] = field(default_factory=list)  # IP 列表
    ticket_refs: List[str] = field(default_factory=list)  # 引用的工单
    error_codes: List[str] = field(default_factory=list)  # 错误码
    raw_matches: Dict[str, List[str]] = field(default_factory=dict)  # 原始匹配结果

    def is_empty(self) -> bool:
        """检查是否有任何匹配"""
        return (
            self.problem_type is None
            and self.priority is None
            and len(self.host_ips) == 0
            and len(self.ticket_refs) == 0
            and len(self.error_codes) == 0
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "problem_type": self.problem_type,
            "priority": self.priority,
            "host_ips": self.host_ips,
            "ticket_refs": self.ticket_refs,
            "error_codes": self.error_codes,
            "raw_matches": self.raw_matches,
        }

    def __str__(self) -> str:
        parts = []
        if self.problem_type:
            parts.append(f"问题类型: {self.problem_type}")
        if self.priority:
            parts.append(f"优先级: {self.priority}")
        if self.host_ips:
            parts.append(f"服务器IP: {', '.join(self.host_ips)}")
        if self.ticket_refs:
            parts.append(f"工单引用: {', '.join(self.ticket_refs)}")
        if self.error_codes:
            parts.append(f"错误码: {', '.join(self.error_codes)}")
        return " | ".join(parts) if parts else "(无匹配)"


@dataclass
class KeywordCategory:
    """关键字分类"""

    name: str
    patterns: List[str]
    max_count: int = 1  # 最大匹配数量，1 表示只取第一个


class KeywordMatcher:
    """关键字匹配器"""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.config_loader = config_loader or ConfigLoader()
        self.keywords_config = self.config_loader.load_keywords()
        self.categories: List[KeywordCategory] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """编译正则表达式模式"""
        keywords = self.keywords_config.get("keywords", {})

        category_defs = [
            ("problem_type", keywords.get("problem_types", []), 1),
            ("priority", keywords.get("priority", []), 1),
            ("host_ips", keywords.get("host_patterns", []), 10),
            ("ticket_refs", keywords.get("ticket_refs", []), 10),
            ("error_codes", keywords.get("error_codes", []), 10),
        ]

        for name, patterns, max_count in category_defs:
            compiled_patterns = []
            for pattern in patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    compiled_patterns.append((pattern, compiled))
                except re.error as e:
                    logger.warning(f"无效的正则表达式 '{pattern}': {e}")
            self.categories.append(
                KeywordCategory(name=name, patterns=compiled_patterns, max_count=max_count)
            )

        logger.info(f"关键字匹配器初始化完成，加载了 {len(self.categories)} 个分类")

    def match(self, text: str) -> MatchResult:
        """
        匹配单个文本

        Args:
            text: 待匹配的文本

        Returns:
            MatchResult: 匹配结果
        """
        result = MatchResult()

        for category in self.categories:
            matches = []
            for pattern_str, compiled in category.patterns:
                found = compiled.findall(text)
                matches.extend(found)

            if matches:
                # 去重
                unique_matches = list(dict.fromkeys(matches))

                # 根据分类处理结果
                if category.name == "problem_type":
                    result.problem_type = unique_matches[0] if unique_matches else None
                elif category.name == "priority":
                    result.priority = unique_matches[0] if unique_matches else None
                elif category.name == "host_ips":
                    result.host_ips = unique_matches[: category.max_count]
                elif category.name == "ticket_refs":
                    result.ticket_refs = unique_matches[: category.max_count]
                elif category.name == "error_codes":
                    result.error_codes = unique_matches[: category.max_count]

                result.raw_matches[category.name] = unique_matches

        return result

    def match_all(self, messages: List[Dict[str, Any]]) -> List[MatchResult]:
        """
        批量匹配消息

        Args:
            messages: 消息列表，每条消息包含 'content' 字段

        Returns:
            匹配结果列表
        """
        results = []
        for msg in messages:
            content = msg.get("content", "")
            if content:
                result = self.match(content)
                results.append(result)

        return results

    def merge_results(self, results: List[MatchResult]) -> MatchResult:
        """
        合并多个匹配结果

        Args:
            results: 匹配结果列表

        Returns:
            合并后的匹配结果
        """
        merged = MatchResult()

        for result in results:
            # 优先保留非空结果
            if merged.problem_type is None and result.problem_type:
                merged.problem_type = result.problem_type

            if merged.priority is None and result.priority:
                merged.priority = result.priority

            # 合并列表（去重）
            for ip in result.host_ips:
                if ip not in merged.host_ips:
                    merged.host_ips.append(ip)

            for ref in result.ticket_refs:
                if ref not in merged.ticket_refs:
                    merged.ticket_refs.append(ref)

            for code in result.error_codes:
                if code not in merged.error_codes:
                    merged.error_codes.append(code)

            # 合并原始匹配
            for key, values in result.raw_matches.items():
                if key not in merged.raw_matches:
                    merged.raw_matches[key] = []
                for v in values:
                    if v not in merged.raw_matches[key]:
                        merged.raw_matches[key].append(v)

        return merged
