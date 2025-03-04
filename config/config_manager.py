from __future__ import annotations
from typing import Optional
import argparse

class ConfigManager:
    """配置管理器单例类
    
    使用单例模式确保全局只有一个配置实例
    """
    _instance: Optional[ConfigManager] = None
    _initialized: bool = False

    def __new__(cls) -> ConfigManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._parser = argparse.ArgumentParser()
            self._initialize_arguments()
            self._args = None
            self._initialized = True

    def _initialize_arguments(self):
        """初始化命令行参数"""
        self._parser.add_argument('--api_key', type=str, default='', help='API key')
        self._parser.add_argument('--base_url', type=str, default='https://a1.aizex.me/v1', help='Base URL')
        self._parser.add_argument('--max_workers', type=int, default=6, help='改作业的最大线程数')
        self._parser.add_argument('--prepare_model', type=str, default='gpt-4o', help='用来生成分标准和参考分数的大模型')
        self._parser.add_argument('--gen_model', type=str, default='gpt-4o-2024-11-20', help='用来生成单个学生分数的大模型')
        self._parser.add_argument('--number_prepare_max', type=int, default=10, help='用来生成改分标准和参考分数的学生作业数量')
        self._parser.add_argument('--number_prepare_min', type=int, default=5, help='用来生成改分标准和参考分数的学生作业数量')
        self._parser.add_argument('--number_gen_max', type=int, default=3, help='生成单个学生分数时用来参考的学生-分数对的数量')
        self._parser.add_argument('--number_gen_min', type=int, default=1, help='生成单个学生分数时用来参考的学生-分数对的数量')
        self._parser.add_argument('--pulling_students_up', type=bool, default=True, help='是否要捞学生一把')
        self._parser.add_argument('--normalized_min', type=int, default=60, help='缩放的最高分')
        self._parser.add_argument('--normalized_max', type=int, default=85, help='缩放的最低分')
        self._parser.add_argument('--original_min', type=int, default=20, help='低于这个分数不缩放')
        self._parser.add_argument('--original_max', type=int, default=85, help='高于这个分数不缩放')
        self._parser.add_argument('--prepare_system_prompt', type=str, default='', help='少样本改作业的系统提示词')
        self._parser.add_argument('--few_shot_learning_system_prompt', type=str, default='', help='少样本学习系统提示词')

    def parse_args(self):
        """解析命令行参数"""
        if self._args is None:
            self._args = self._parser.parse_args()
        return self._args

    @property
    def config(self):
        """获取配置实例"""
        return self.parse_args()

# 全局配置实例
config = ConfigManager()