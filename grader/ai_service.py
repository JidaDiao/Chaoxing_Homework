from typing import Dict, List, Optional
from grader.interfaces import AIService
from openai import OpenAI
import json
import re
import logging


class OpenAIService(AIService):
    """OpenAI服务实现
    
    封装与OpenAI API的交互，提供生成完成结果和提取JSON数据的功能。
    """
    
    def __init__(self, api_key: str, base_url: str):
        """初始化OpenAI服务
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def generate_completion(self, messages: List[Dict]) -> str:
        """生成AI完成结果
        
        Args:
            messages: 输入消息列表
            
        Returns:
            AI生成的结果
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",  # 可以通过配置参数传入
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"生成完成结果时发生错误: {str(e)}")
            return ""
    
    def extract_json_from_response(self, response_content: str) -> Optional[Dict]:
        """从AI响应中提取JSON数据
        
        Args:
            response_content: AI响应内容
            
        Returns:
            提取的JSON数据，如果提取失败则返回None
        """
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            json_str = json_str.replace("'", '"')
            try:
                json_data = json.loads(json_str)
                return json_data
            except json.JSONDecodeError as e:
                logging.error(f"JSON解析错误，原内容: {response_content}")
                return None
        else:
            logging.error("未找到JSON格式内容")
            return None