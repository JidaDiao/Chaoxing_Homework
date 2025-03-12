import json
import os
from typing import Dict
from grader.interfaces import FileStorage
import logging


class LocalFileStorage(FileStorage):
    """本地文件存储实现
    
    处理本地文件系统的读写操作。
    """
    
    def save_json(self, data: Dict, filename: str) -> None:
        """保存JSON数据到文件
        
        Args:
            data: 要保存的数据
            filename: 文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, sort_keys=True, ensure_ascii=False)
            logging.info(f"JSON数据已保存到: {filename}")
        except Exception as e:
            logging.error(f"保存JSON数据时发生错误: {str(e)}")
    
    def load_json(self, filename: str) -> Dict:
        """从文件加载JSON数据
        
        Args:
            filename: 文件名
            
        Returns:
            加载的JSON数据
        """
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                data = json.load(file)
            logging.info(f"已从 {filename} 加载JSON数据")
            return data
        except FileNotFoundError:
            logging.error(f"文件未找到: {filename}")
            return {}
        except json.JSONDecodeError:
            logging.error(f"JSON文件解析错误: {filename}")
            return {}
    
    def save_text(self, text: str, filename: str) -> None:
        """保存文本到文件
        
        Args:
            text: 要保存的文本
            filename: 文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(text)
            logging.info(f"文本已保存到: {filename}")
        except Exception as e:
            logging.error(f"保存文本时发生错误: {str(e)}")
    
    def load_text(self, filename: str) -> str:
        """从文件加载文本
        
        Args:
            filename: 文件名
            
        Returns:
            加载的文本
        """
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                text = file.read()
            logging.info(f"已从 {filename} 加载文本")
            return text
        except FileNotFoundError:
            logging.error(f"文件未找到: {filename}")
            return ""
        except Exception as e:
            logging.error(f"加载文本时发生错误: {str(e)}")
            return ""