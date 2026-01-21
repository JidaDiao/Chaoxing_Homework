from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
from openai import OpenAI


class IOpenAIClient(ABC):
    """OpenAI客户端接口，负责与OpenAI API的所有交互"""
    
    @abstractmethod
    def __init__(self, api_key: str, base_url: str):
        """初始化OpenAI客户端
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
        """
        pass
    
    @abstractmethod
    def create_completion(self, model: str, messages: List[Dict[str, Any]]) -> Any:
        """创建聊天完成请求
        
        Args:
            model: 使用的模型名称
            messages: 消息列表
            
        Returns:
            API响应对象
        """
        pass
    
    @abstractmethod
    def extract_json_from_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """从响应内容中提取JSON数据
        
        Args:
            response_content: API响应的文本内容
            
        Returns:
            提取的JSON数据，如果提取失败则返回None
        """
        pass


class IMessageBuilder(ABC):
    """消息构建器接口，负责构建发送给OpenAI的消息格式"""
    
    @staticmethod
    @abstractmethod
    def create_student_messages_with_images(homework_data: Dict[str, Any], student_name: str) -> List[Dict[str, Any]]:
        """创建包含图片的消息列表
        
        Args:
            homework_data: 作业数据，包含学生答案和题目信息
            student_name: 学生姓名
            
        Returns:
            包含学生答案和图片的消息列表
        """
        pass
    

    @staticmethod
    @abstractmethod
    def download_images(image_urls_map: Dict[str, str]) -> List[Dict[str, Any]]:
        """下载学生提交的所有图片

        Args:
            image_urls_map: 包含图片标识和图片URL的字典

        Returns:
            包含已下载图片的消息列表
        """
        pass

    @staticmethod
    @abstractmethod
    def gen_prepare_system_prompt(homework_data: Dict[str, Any], number: int) -> List[Dict[str, str]]:
        """生成系统提示信息
        
        Args:
            homework_data: 作业数据，包含题目信息和答案
            number: 需要处理的题目数量
            
        Returns:
            包含系统提示信息的消息列表
        """
        pass
    
    @staticmethod
    @abstractmethod
    def gen_few_shot_learning_system_prompt(homework_data: Dict[str, Any], grading_standard: str) -> List[Dict[str, str]]:
        """生成少样本学习系统提示
        
        Args:
            homework_data: 作业数据，包含题目信息和答案
            grading_standard: 评分标准
            
        Returns:
            包含系统提示信息的消息列表
        """
        pass


class IScoreProcessor(ABC):
    """分数处理器接口，负责处理和管理分数相关的操作"""
    
    @abstractmethod
    def __init__(self, ai_client: IOpenAIClient):
        """初始化分数处理器
        
        Args:
            ai_client: OpenAI客户端实例
        """
        pass
    
    @abstractmethod
    def prepare_score(self, prepare_system_prompt: List[Dict[str, str]], number: int) -> Tuple[str, List[str]]:
        """准备参考分数和评分标准
        
        Args:
            prepare_system_prompt: 准备阶段的系统提示
            number: 需要处理的答案数量
            
        Returns:
            生成的评分标准和已处理的学生列表
        """
        pass
    
    @abstractmethod
    def gen_score(self, number_gen: int, selected_dict_uncorrected: Dict[str, List[Dict[str, Any]]], 
                 few_shot_learning_system_prompt: List[Dict[str, str]]) -> None:
        """生成学生分数
        
        Args:
            number_gen: 用于参考的样本数量
            selected_dict_uncorrected: 选定的未批改答案
            few_shot_learning_system_prompt: 少样本学习系统提示
        """
        pass
    
    @abstractmethod
    def normalize_score(self, student_scores: Dict[str, float], normalized_min: float = 60, 
                       normalized_max: float = 85, original_min: float = 20, 
                       original_max: float = 90) -> Dict[str, float]:
        """对学生成绩进行归一化处理
        
        Args:
            student_scores: 包含学生最终成绩的字典
            normalized_min: 归一化后的最小分数
            normalized_max: 归一化后的最大分数
            original_min: 原始成绩的最小值
            original_max: 原始成绩的最大值
            
        Returns:
            归一化处理后的成绩字典
        """
        pass


class IScoreSessionProcessor(ABC):
    """Score processor interface for session-based grading."""

    @abstractmethod
    def initialize_context(self, homework_data: Dict[str, Any], homework_id: str) -> Any:
        """Initialize grading context for a homework session."""
        pass

    @abstractmethod
    def attach_grading_standard(self, grading_standard: str) -> str:
        """Attach an existing grading standard to the session."""
        pass

    @abstractmethod
    def generate_grading_standard(self, sample_students: Dict[str, Any], number: int) -> str:
        """Generate grading standard and sample scores."""
        pass

    @abstractmethod
    def grade_students_batch(self, students: Dict[str, Any]) -> Any:
        """Grade a batch of students in a session."""
        pass

    @abstractmethod
    def get_all_scores(self) -> Dict[str, Dict[str, Any]]:
        """Return scores in legacy schema."""
        pass

    @abstractmethod
    def get_grading_standard(self) -> str:
        """Return grading standard text."""
        pass


class IFileManager(ABC):
    """文件管理器接口，负责文件操作，包括读写JSON、Excel等"""
    
    @staticmethod
    @abstractmethod
    def save_grades(scores_to_save: Dict[str, float]) -> Dict[str, float]:
        """将成绩保存到Excel文件
        
        Args:
            scores_to_save: 需要保存的成绩字典
            
        Returns:
            保存的成绩字典
        """
        pass
    
    @staticmethod
    @abstractmethod
    def import_json_file(file_path: str) -> Dict[str, Any]:
        """导入JSON文件
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            导入的JSON数据
        """
        pass
    
    @staticmethod
    @abstractmethod
    def save_json_file(data: Dict[str, Any], file_path: str, indent: int = 4, 
                      sort_keys: bool = True, ensure_ascii: bool = False) -> None:
        """保存JSON文件
        
        Args:
            data: 需要保存的数据
            file_path: 保存路径
            indent: 缩进空格数
            sort_keys: 是否对键进行排序
            ensure_ascii: 是否确保ASCII编码
        """
        pass


class IHomeworkProcessor(ABC):
    """作业处理器接口，负责处理作业目录和学生答案"""
    
    @staticmethod
    @abstractmethod
    def process_homework_directories() -> List[str]:
        """处理作业目录
        
        Returns:
            作业目录路径列表
        """
        pass
    
    @staticmethod
    @abstractmethod
    def process_student_answers(homework_data: Dict[str, Any], 
                               message_builder: IMessageBuilder) -> Dict[str, List[Dict[str, Any]]]:
        """处理学生答案
        
        Args:
            homework_data: 作业数据
            message_builder: 消息构建器实例
            
        Returns:
            处理后的学生答案
        """
        pass


class IHomeworkGrader(ABC):
    """作业批改器接口，作为协调者使用其他专门的类来完成工作"""
    
    @abstractmethod
    def __init__(self, api_key: str, base_url: str):
        """初始化作业批改器
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
        """
        pass
    
    @abstractmethod
    def run(self) -> None:
        """运行作业批改流程
        
        协调各个组件完成作业批改的完整流程，包括：
        1. 导入作业数据
        2. 处理学生答案
        3. 生成评分标准
        4. 批改作业并生成分数
        5. 保存结果
        """
        pass
