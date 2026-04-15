"""
配置加载器测试
"""

import os
import unittest
from pathlib import Path
import sys
import tempfile
import yaml

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config_loader import ConfigLoader
from src.core.exceptions import ConfigLoadError


class TestConfigLoader(unittest.TestCase):
    """ConfigLoader 测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.original_dir = Path(__file__).parent.parent / "config"
        cls.loader = ConfigLoader(config_dir=str(cls.original_dir))

    def test_load_keywords(self):
        """测试加载关键字配置"""
        config = self.loader.load_keywords()

        self.assertIsInstance(config, dict)
        self.assertIn("keywords", config)

        keywords = config["keywords"]
        self.assertIn("problem_types", keywords)
        self.assertIn("priority", keywords)
        self.assertIn("host_patterns", keywords)

    def test_load_field_mapping(self):
        """测试加载字段映射配置"""
        config = self.loader.load_field_mapping()

        self.assertIsInstance(config, dict)
        self.assertIn("ticket_system", config)

        ticket_system = config["ticket_system"]
        self.assertIn("fields", ticket_system)
        self.assertIsInstance(ticket_system["fields"], list)

    def test_load_settings(self):
        """测试加载全局设置"""
        config = self.loader.load_settings()

        self.assertIsInstance(config, dict)
        self.assertIn("welink", config)
        self.assertIn("workorder", config)
        self.assertIn("logging", config)

    def test_load_nonexistent_config(self):
        """测试加载不存在的配置文件"""
        loader = ConfigLoader(config_dir="nonexistent_dir")

        with self.assertRaises(ConfigLoadError):
            loader.load("nonexistent_config")

    def test_cache_functionality(self):
        """测试缓存功能"""
        config1 = self.loader.load_keywords()
        config2 = self.loader.load_keywords()

        self.assertEqual(config1, config2)

    def test_reload(self):
        """测试重新加载配置"""
        config1 = self.loader.load_keywords()
        config2 = self.loader.reload("keywords")

        self.assertEqual(config1, config2)

    def test_clear_cache(self):
        """测试清除缓存"""
        self.loader.load_keywords()
        self.assertIn("keywords", self.loader._cache)

        self.loader.clear_cache()
        self.assertEqual(len(self.loader._cache), 0)

    def test_resolve_env_var(self):
        """测试环境变量解析"""
        os.environ["TEST_VAR"] = "test_value"

        loader = ConfigLoader()
        result = loader._resolve_env_var("${TEST_VAR}")

        self.assertEqual(result, "test_value")

        del os.environ["TEST_VAR"]

    def test_resolve_env_var_not_found(self):
        """测试环境变量未找到"""
        loader = ConfigLoader()
        result = loader._resolve_env_var("${NONEXISTENT_VAR_12345}")

        # 应该返回原始值
        self.assertEqual(result, "${NONEXISTENT_VAR_12345}")

    def test_parse_regex(self):
        """测试正则表达式解析"""
        loader = ConfigLoader()

        result = loader._parse_regex("/test.*pattern/")
        self.assertEqual(result, "test.*pattern")

        result = loader._parse_regex("plaintext")
        self.assertEqual(result, "plaintext")

    def test_process_config_recursive(self):
        """测试递归处理配置"""
        loader = ConfigLoader()

        config = {
            "level1": {
                "level2": ["/pattern/", "plain"]
            },
            "single": "/another/"
        }

        processed = loader._process_config(config)

        self.assertEqual(processed["single"], "another")
        self.assertEqual(processed["level1"]["level2"][0], "pattern")
        self.assertEqual(processed["level1"]["level2"][1], "plain")


class TestConfigLoaderWithTempDir(unittest.TestCase):
    """使用临时目录的配置加载器测试"""

    def setUp(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = ConfigLoader(config_dir=self.temp_dir)

    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_empty_config(self):
        """测试加载空配置文件"""
        config_path = Path(self.temp_dir) / "empty.yaml"
        config_path.write_text("")

        with self.assertRaises(ConfigLoadError):
            self.loader.load("empty")

    def test_load_invalid_yaml(self):
        """测试加载无效 YAML"""
        config_path = Path(self.temp_dir) / "invalid.yaml"
        config_path.write_text("key: [unclosed bracket")

        with self.assertRaises(ConfigLoadError):
            self.loader.load("invalid")

    def test_create_and_load(self):
        """测试创建并加载配置文件"""
        config_path = Path(self.temp_dir) / "test.yaml"
        test_config = {
            "test_key": "test_value",
            "nested": {
                "key": "value"
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(test_config, f)

        loaded = self.loader.load("test")

        self.assertEqual(loaded["test_key"], "test_value")
        self.assertEqual(loaded["nested"]["key"], "value")


if __name__ == "__main__":
    unittest.main()
