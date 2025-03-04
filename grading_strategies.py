from abc import ABC, abstractmethod
from typing import Dict, Any
from openai import OpenAI
from config.config_manager import config

class GradingStrategy(ABC):
    """评分策略接口
    
    定义评分策略的接口，所有具体的评分策略都需要实现这个接口
    """
    
    @abstractmethod
    def grade(self, student_answers: Dict[str, Any], homework_data: Dict[str, Any]) -> Dict[str, Any]:
        """评分方法
        
        Args:
            student_answers: 学生答案数据
            homework_data: 作业数据
            
        Returns:
            Dict[str, Any]: 评分结果
        """
        pass

class FewShotLearningStrategy(GradingStrategy):
    """少样本学习评分策略
    
    使用少样本学习方法对学生作业进行评分
    """
    
    def __init__(self, client: OpenAI):
        self.client = client
        
    def grade(self, student_answers: Dict[str, Any], homework_data: Dict[str, Any]) -> Dict[str, Any]:
        # 实现少样本学习评分逻辑
        system_prompt = self._generate_system_prompt(homework_data)
        response = self.client.chat.completions.create(
            model=config.gen_model,
            messages=system_prompt
        )
        return self._process_response(response)
    
    def _generate_system_prompt(self, homework_data: Dict[str, Any]) -> list:
        # 生成系统提示
        question_stem = "###\n"
        for key, value in homework_data["题目"].items():
            question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"
            
        system_prompt = config.few_shot_learning_system_prompt.format(
            question_stem=question_stem,
            grading_standard=homework_data.get("grading_standard", "")
        )
        
        return [{"role": "system", "content": system_prompt}]
    
    def _process_response(self, response: Any) -> Dict[str, Any]:
        # 处理API响应
        try:
            content = response.choices[0].message.content
            return self._extract_scores(content)
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_scores(self, content: str) -> Dict[str, Any]:
        # 从响应中提取分数
        import re
        import json
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format"}
        return {"error": "No JSON found in response"}

class StandardGradingStrategy(GradingStrategy):
    """标准评分策略
    
    使用预定义的评分标准对学生作业进行评分
    """
    
    def __init__(self, client: OpenAI):
        self.client = client
        
    def grade(self, student_answers: Dict[str, Any], homework_data: Dict[str, Any]) -> Dict[str, Any]:
        # 实现标准评分逻辑
        system_prompt = self._generate_system_prompt(homework_data)
        response = self.client.chat.completions.create(
            model=config.prepare_model,
            messages=system_prompt
        )
        return self._process_response(response)
    
    def _generate_system_prompt(self, homework_data: Dict[str, Any]) -> list:
        # 生成系统提示
        question_stem = "###\n"
        for key, value in homework_data["题目"].items():
            question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"
            
        system_prompt = config.prepare_system_prompt.format(
            question_stem=question_stem,
            number=str(config.number_prepare_max),
            number_=str(config.number_prepare_max-1)
        )
        
        return [{"role": "system", "content": system_prompt}]
    
    def _process_response(self, response: Any) -> Dict[str, Any]:
        # 处理API响应
        try:
            content = response.choices[0].message.content
            return self._extract_scores(content)
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_scores(self, content: str) -> Dict[str, Any]:
        # 从响应中提取分数
        import re
        import json
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format"}
        return {"error": "No JSON found in response"}