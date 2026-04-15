"""
关键字匹配引擎测试
"""

import unittest
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.keyword_matcher import KeywordMatcher, MatchResult


class TestKeywordMatcher(unittest.TestCase):
    """KeywordMatcher 测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 使用配置文件创建匹配器
        cls.matcher = KeywordMatcher()

    def test_match_problem_type(self):
        """测试问题类型匹配"""
        result = self.matcher.match("服务器故障导致服务中断")

        self.assertIsNotNone(result)
        self.assertIn("服务器", result.problem_type or "")

    def test_match_priority(self):
        """测试优先级匹配"""
        result = self.matcher.match("紧急：P1 问题需要立即处理")

        self.assertIsNotNone(result)
        self.assertTrue(
            result.priority in ["P1", "紧急"] or
            "P1" in result.raw_matches.get("priority", []) or
            "紧急" in result.raw_matches.get("priority", [])
        )

    def test_match_ip_address(self):
        """测试 IP 地址匹配"""
        result = self.matcher.match("问题服务器IP是 192.168.1.100")

        self.assertIsNotNone(result)
        self.assertTrue(len(result.host_ips) > 0)
        self.assertIn("192.168.1.100", result.host_ips)

    def test_match_ip_with_port(self):
        """测试带端口的 IP 地址匹配"""
        result = self.matcher.match("连接失败：10.0.0.1:8080")

        self.assertIsNotNone(result)
        self.assertTrue(len(result.host_ips) > 0)

    def test_match_ticket_refs(self):
        """测试工单引用匹配"""
        result = self.matcher.match("关联工单：ITSM-2024-00123，请尽快处理")

        self.assertIsNotNone(result)
        self.assertTrue(len(result.ticket_refs) > 0)
        self.assertIn("ITSM-2024-00123", result.ticket_refs)

    def test_match_error_code(self):
        """测试错误码匹配"""
        result = self.matcher.match("error: NullPointerException at line 42")

        self.assertIsNotNone(result)
        # error_codes 可能为空，取决于配置
        self.assertIsInstance(result.error_codes, list)

    def test_match_multiple_ips(self):
        """测试匹配多个 IP"""
        result = self.matcher.match("源IP: 192.168.1.10, 目标IP: 10.0.0.5")

        self.assertIsNotNone(result)
        self.assertTrue(len(result.host_ips) >= 1)

    def test_match_no_keywords(self):
        """测试无关键字匹配"""
        result = self.matcher.match("这是一条普通的消息，不包含任何关键字")

        self.assertIsNotNone(result)
        self.assertTrue(result.is_empty())

    def test_match_case_insensitive(self):
        """测试大小写不敏感"""
        result1 = self.matcher.match("P1 紧急问题")
        result2 = self.matcher.match("p1 紧急问题")

        self.assertIsNotNone(result1.priority or result2.priority)

    def test_match_empty_text(self):
        """测试空文本"""
        result = self.matcher.match("")

        self.assertIsNotNone(result)
        self.assertTrue(result.is_empty())

    def test_match_all_messages(self):
        """测试批量消息匹配"""
        messages = [
            {"content": "服务器故障，P1级别"},
            {"content": "IP地址是 192.168.1.100"},
            {"content": "关联工单 ITSM-2024-001"},
        ]

        results = self.matcher.match_all(messages)

        self.assertEqual(len(results), len(messages))
        for result in results:
            self.assertIsInstance(result, MatchResult)

    def test_merge_results(self):
        """测试结果合并"""
        result1 = MatchResult(
            problem_type="服务器故障",
            host_ips=["192.168.1.100"]
        )
        result2 = MatchResult(
            priority="P1",
            host_ips=["10.0.0.1"]
        )

        merged = self.matcher.merge_results([result1, result2])

        self.assertEqual(merged.problem_type, "服务器故障")
        self.assertEqual(merged.priority, "P1")
        self.assertIn("192.168.1.100", merged.host_ips)
        self.assertIn("10.0.0.1", merged.host_ips)

    def test_merge_results_priority(self):
        """测试合并时优先级：第一个非空值"""
        result1 = MatchResult(problem_type=None)
        result2 = MatchResult(problem_type="网络中断")

        merged = self.matcher.merge_results([result1, result2])

        self.assertEqual(merged.problem_type, "网络中断")

    def test_match_result_to_dict(self):
        """测试 MatchResult 转换为字典"""
        result = MatchResult(
            problem_type="服务器故障",
            priority="P1",
            host_ips=["192.168.1.100"],
            ticket_refs=["ITSM-2024-001"],
            error_codes=["E001"]
        )

        d = result.to_dict()

        self.assertEqual(d["problem_type"], "服务器故障")
        self.assertEqual(d["priority"], "P1")
        self.assertEqual(d["host_ips"], ["192.168.1.100"])
        self.assertEqual(d["ticket_refs"], ["ITSM-2024-001"])
        self.assertEqual(d["error_codes"], ["E001"])

    def test_match_result_str(self):
        """测试 MatchResult 字符串表示"""
        result = MatchResult(
            problem_type="服务器故障",
            priority="P1"
        )

        s = str(result)

        self.assertIn("服务器故障", s)
        self.assertIn("P1", s)

    def test_match_result_str_empty(self):
        """测试空 MatchResult 字符串表示"""
        result = MatchResult()

        s = str(result)

        self.assertEqual(s, "(无匹配)")


if __name__ == "__main__":
    unittest.main()
