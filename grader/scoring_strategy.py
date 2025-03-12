from typing import Dict
from grader.interfaces import ScoringStrategy
import json
import re
import logging


class DefaultScoringStrategy(ScoringStrategy):
    """默认评分策略实现
    
    基于AI模型响应实现的评分策略，从AI响应中提取JSON格式的分数。
    """
    
    def score(self, student_answers: Dict, reference_data: Dict) -> Dict:
        """根据学生答案和参考数据生成分数
        
        Args:
            student_answers: 学生答案数据
            reference_data: 参考数据，包括标准答案、评分规则等
            
        Returns:
            包含学生分数的字典
        """
        # 从AI响应中提取JSON格式的分数
        response_content = reference_data.get('response_content', '')
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            json_str = json_str.replace("'", '"')
            try:
                json_data = json.loads(json_str)
                return json_data.get('student_scores', {})
            except json.JSONDecodeError as e:
                logging.error(f"JSON解析错误，原内容: {response_content}")
                return {}
        else:
            logging.error("未找到JSON格式内容")
            return {}