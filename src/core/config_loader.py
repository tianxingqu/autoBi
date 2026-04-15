"""
配置加载器
负责加载和解析 YAML 配置文件
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger

from .exceptions import ConfigLoadError


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Any] = {}

    def _resolve_env_var(self, value: str) -> str:
        """
        解析环境变量引用
        例如: ${USERNAME} -> actual_username
        """
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, value)
        return value

    def _parse_regex(self, value: str) -> str:
        """
        解析正则表达式标记
        例如: /pattern/ -> pattern
        """
        if isinstance(value, str) and value.startswith("/") and value.endswith("/"):
            return value[1:-1]
        return value

    def _process_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """处理配置：解析环境变量和正则表达式"""
        processed = {}
        for key, value in config.items():
            if isinstance(value, dict):
                processed[key] = self._process_config(value)
            elif isinstance(value, list):
                processed[key] = [
                    self._resolve_env_var(
                        self._parse_regex(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                processed[key] = self._resolve_env_var(self._parse_regex(value))
            else:
                processed[key] = value
        return processed

    def load(self, config_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载配置文件

        Args:
            config_name: 配置文件名（不含扩展名）
            use_cache: 是否使用缓存

        Returns:
            配置字典
        """
        if use_cache and config_name in self._cache:
            return self._cache[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"

        if not config_path.exists():
            raise ConfigLoadError(f"配置文件不存在: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config is None:
                raise ConfigLoadError(f"配置文件为空: {config_path}")

            processed = self._process_config(config)
            self._cache[config_name] = processed

            logger.info(f"配置文件加载成功: {config_path}")
            return processed

        except yaml.YAMLError as e:
            raise ConfigLoadError(f"配置文件解析失败 {config_path}: {e}")
        except Exception as e:
            raise ConfigLoadError(f"配置文件读取失败 {config_path}: {e}")

    def load_keywords(self) -> Dict[str, Any]:
        """加载关键字配置"""
        return self.load("keywords")

    def load_field_mapping(self) -> Dict[str, Any]:
        """加载字段映射配置"""
        return self.load("field-mapping")

    def load_settings(self) -> Dict[str, Any]:
        """加载全局设置"""
        return self.load("settings")

    def reload(self, config_name: str) -> Dict[str, Any]:
        """重新加载配置（清除缓存）"""
        if config_name in self._cache:
            del self._cache[config_name]
        return self.load(config_name)

    def clear_cache(self):
        """清除所有缓存"""
        self._cache.clear()
