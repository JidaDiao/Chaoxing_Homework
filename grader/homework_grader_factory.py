from typing import Dict
from grader.interfaces import HomeworkGraderFactory, HomeworkGrader
from grader.homework_grader import DefaultHomeworkGrader
from grader.ai_service import OpenAIService
from grader.file_storage import LocalFileStorage
from grader.image_processor import DefaultImageProcessor
from grader.score_normalizer import DefaultScoreNormalizer
from grader.message_factory import OpenAIMessageFactory


class DefaultHomeworkGraderFactory(HomeworkGraderFactory):
    """默认作业批改器工厂实现
    
    创建作业批改器实例，并注入所需的依赖。
    """
    
    def create_grader(self, api_key: str, base_url: str) -> HomeworkGrader:
        """创建作业批改器
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
            
        Returns:
            作业批改器实例
        """
        # 创建依赖组件
        ai_service = OpenAIService(api_key, base_url)
        file_storage = LocalFileStorage()
        image_processor = DefaultImageProcessor()
        score_normalizer = DefaultScoreNormalizer()
        message_factory = OpenAIMessageFactory()
        
        # 创建并返回作业批改器实例
        return DefaultHomeworkGrader(
            ai_service=ai_service,
            file_storage=file_storage,
            image_processor=image_processor,
            score_normalizer=score_normalizer,
            message_factory=message_factory
        )