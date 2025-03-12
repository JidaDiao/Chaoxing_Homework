from typing import Dict
from grader.interfaces import ScoringCommand, AIService, ScoringStrategy


class DefaultScoringCommand(ScoringCommand):
    """默认评分命令实现
    
    封装评分请求，使用AI服务和评分策略执行评分操作。
    """
    
    def __init__(self, ai_service: AIService, scoring_strategy: ScoringStrategy, 
                 student_answers: Dict, reference_data: Dict):
        """初始化评分命令
        
        Args:
            ai_service: AI服务实例
            scoring_strategy: 评分策略实例
            student_answers: 学生答案数据
            reference_data: 参考数据，包括标准答案、评分规则等
        """
        self.ai_service = ai_service
        self.scoring_strategy = scoring_strategy
        self.student_answers = student_answers
        self.reference_data = reference_data
    
    def execute(self) -> Dict:
        """执行评分命令
        
        使用AI服务生成评分结果，然后使用评分策略处理结果。
        
        Returns:
            评分结果
        """
        # 准备消息列表
        messages = self.reference_data.get('messages', [])
        
        # 使用AI服务生成完成结果
        response_content = self.ai_service.generate_completion(messages)
        
        # 将响应内容添加到参考数据中
        self.reference_data['response_content'] = response_content
        
        # 使用评分策略生成分数
        return self.scoring_strategy.score(self.student_answers, self.reference_data)