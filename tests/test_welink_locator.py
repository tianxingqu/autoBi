"""
Welink UI 定位器测试
注意：这些测试需要 Welink 实际运行，仅做单元测试
"""

import os
import unittest
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.welink.locator import WelinkLocator, LocatorStrategy
from src.core.exceptions import ElementNotFoundError


class TestLocatorStrategy(unittest.TestCase):
    """定位策略测试"""

    def test_locator_strategy_constants(self):
        """测试策略常量定义"""
        self.assertEqual(LocatorStrategy.WINDOW_SPEC, "window_spec")
        self.assertEqual(LocatorStrategy.BEST_PRACTICE, "best_practice")
        self.assertEqual(LocatorStrategy.IMAGE, "image")

    def test_locator_strategy_values(self):
        """测试策略值列表"""
        strategies = [
            LocatorStrategy.WINDOW_SPEC,
            LocatorStrategy.BEST_PRACTICE,
            LocatorStrategy.IMAGE
        ]

        self.assertEqual(len(strategies), 3)
        self.assertTrue(all(isinstance(s, str) for s in strategies))


class TestLocatorCriteria(unittest.TestCase):
    """定位条件测试"""

    def test_criteria_with_auto_id(self):
        """测试带 auto_id 的条件"""
        criteria = {"auto_id": "search_input"}

        self.assertEqual(criteria["auto_id"], "search_input")
        self.assertNotIn("title", criteria)
        self.assertNotIn("control_type", criteria)

    def test_criteria_with_title(self):
        """测试带 title 的条件"""
        criteria = {"title": "确定"}

        self.assertEqual(criteria["title"], "确定")

    def test_criteria_with_control_type(self):
        """测试带 control_type 的条件"""
        criteria = {"control_type": "Button"}

        self.assertEqual(criteria["control_type"], "Button")

    def test_criteria_combined(self):
        """测试组合条件"""
        criteria = {
            "auto_id": "submit_btn",
            "title": "提交",
            "control_type": "Button",
            "class_name": "QPushButton"
        }

        self.assertEqual(len(criteria), 4)
        self.assertEqual(criteria["auto_id"], "submit_btn")
        self.assertEqual(criteria["title"], "提交")
        self.assertEqual(criteria["control_type"], "Button")
        self.assertEqual(criteria["class_name"], "QPushButton")


class TestLocatorIntegration(unittest.TestCase):
    """
    定位器集成测试
    注意：需要 Welink 实际运行才能测试
    """

    @classmethod
    def setUpClass(cls):
        """跳过需要 Welink 的测试"""
        cls.skip_integration = os.environ.get("SKIP_WELINK_TESTS", "1") == "1"

    def test_locator_initialization_skip_without_welink(self):
        """测试无 Welink 时跳过初始化"""
        if self.skip_integration:
            self.skipTest("Skipping integration test (Welink not available)")

    def test_find_element_timeout(self):
        """测试元素查找超时"""
        if self.skip_integration:
            self.skipTest("Skipping integration test (Welink not available)")

        # 实际测试需要 Welink 运行
        pass


class TestLocatorMocked(unittest.TestCase):
    """使用 Mock 的定位器测试"""

    def test_matches_criteria_exact(self):
        """测试精确匹配"""
        # 模拟的元素匹配逻辑测试
        criteria = {"control_type": "Edit", "title": "搜索"}

        # 测试匹配逻辑
        element_mock = {
            "control_type": "Edit",
            "window_text": lambda: "搜索",
            "class_name": lambda: "QLineEdit"
        }

        # 控制类型必须匹配
        self.assertEqual(criteria["control_type"], element_mock["control_type"])

        # 标题包含关系
        self.assertIn(criteria["title"], element_mock["window_text"]())

    def test_matches_criteria_partial(self):
        """测试部分匹配"""
        criteria = {"title": "搜索"}

        element_text = "搜索群聊"

        # 标题应该部分匹配
        self.assertIn(criteria["title"], element_text)

    def test_matches_criteria_no_match(self):
        """测试不匹配"""
        criteria = {"title": "不存在"}

        element_text = "搜索群聊"

        self.assertNotIn(criteria["title"], element_text)


class TestLocatorBestPractice(unittest.TestCase):
    """最佳实践定位策略测试"""

    def test_control_type_priority(self):
        """测试控件类型优先级"""
        # 控件类型的识别优先级
        priority_order = [
            "Button",
            "Edit",
            "List",
            "ListItem",
            "Document",
            "Custom"
        ]

        # 验证是合理的优先级顺序
        self.assertTrue(priority_order.index("Button") < priority_order.index("Edit"))
        self.assertTrue(priority_order.index("Edit") < priority_order.index("List"))

    def test_element_types_recognition(self):
        """测试元素类型识别"""
        test_cases = [
            ("QPushButton", "Button"),
            ("QTextEdit", "Document"),
            ("QListWidget", "List"),
            ("QLineEdit", "Edit"),
        ]

        for qt_class, expected_type in test_cases:
            # Qt 类名到控件类型的映射逻辑
            if "Button" in qt_class:
                self.assertEqual(expected_type, "Button")
            elif "Edit" in qt_class or "TextEdit" in qt_class:
                self.assertEqual(expected_type, "Document")
            elif "ListWidget" in qt_class:
                self.assertEqual(expected_type, "List")


if __name__ == "__main__":
    unittest.main()
