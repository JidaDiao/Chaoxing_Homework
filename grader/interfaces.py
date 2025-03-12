from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import json


# 策略模式 - 评分策略接口
class ScoringStrategy(ABC):
    """评分策略接口
    
    定义了不同评分策略的通用接口，允许在运行时切换不同的评分算法。
    """
    
    @abstractmethod
    def score(self, student_answers: Dict, reference_data: Dict) -> Dict:
        """根据学生答案和参考数据生成分数
        
        Args:
            student_answers: 学生答案数据
            reference_data: 参考数据，包括标准答案、评分规则等
            
        Returns:
            包含学生分数的字典
        """
        pass


# 工厂模式 - 消息创建工厂接口
class MessageFactory(ABC):
    """消息创建工厂接口
    
    负责创建不同类型的消息，用于与AI模型交互。
    """
    
    @abstractmethod
    def create_system_message(self, content: str) -> Dict:
        """创建系统消息
        
        Args:
            content: 消息内容
            
        Returns:
            系统消息字典
        """
        pass
    
    @abstractmethod
    def create_user_message(self, content: str) -> Dict:
        """创建用户消息
        
        Args:
            content: 消息内容
            
        Returns:
            用户消息字典
        """
        pass
    
    @abstractmethod
    def create_image_message(self, image_data: str) -> Dict:
        """创建包含图片的消息
        
        Args:
            image_data: 图片数据（Base64编码）
            
        Returns:
            包含图片的消息字典
        """
        pass


# 命令模式 - 评分命令接口
class ScoringCommand(ABC):
    """评分命令接口
    
    封装评分请求，使请求的发送者和接收者解耦。
    """
    
    @abstractmethod
    def execute(self) -> Dict:
        """执行评分命令
        
        Returns:
            评分结果
        """
        pass


# 观察者模式 - 评分结果观察者接口
class ScoreObserver(ABC):
    """评分结果观察者接口
    
    当评分结果更新时接收通知。
    """
    
    @abstractmethod
    def update(self, scores: Dict) -> None:
        """接收评分结果更新
        
        Args:
            scores: 更新的评分结果
        """
        pass


# 观察者模式 - 评分结果主题接口
class ScoreSubject(ABC):
    """评分结果主题接口
    
    管理观察者并在评分结果更新时通知它们。
    """
    
    @abstractmethod
    def attach(self, observer: ScoreObserver) -> None:
        """添加观察者
        
        Args:
            observer: 要添加的观察者
        """
        pass
    
    @abstractmethod
    def detach(self, observer: ScoreObserver) -> None:
        """移除观察者
        
        Args:
            observer: 要移除的观察者
        """
        pass
    
    @abstractmethod
    def notify(self) -> None:
        """通知所有观察者"""
        pass


# AI服务接口
class AIService(ABC):
    """AI服务接口
    
    封装与AI模型的交互。
    """
    
    @abstractmethod
    def generate_completion(self, messages: List[Dict]) -> str:
        """生成AI完成结果
        
        Args:
            messages: 输入消息列表
            
        Returns:
            AI生成的结果
        """
        pass
    
    @abstractmethod
    def extract_json_from_response(self, response_content: str) -> Optional[Dict]:
        """从AI响应中提取JSON数据
        
        Args:
            response_content: AI响应内容
            
        Returns:
            提取的JSON数据，如果提取失败则返回None
        """
        pass


# 文件存储接口
class FileStorage(ABC):
    """文件存储接口
    
    处理文件的读写操作。
    """
    
    @abstractmethod
    def save_json(self, data: Dict, filename: str) -> None:
        """保存JSON数据到文件
        
        Args:
            data: 要保存的数据
            filename: 文件名
        """
        pass
    
    @abstractmethod
    def load_json(self, filename: str) -> Dict:
        """从文件加载JSON数据
        
        Args:
            filename: 文件名
            
        Returns:
            加载的JSON数据
        """
        pass
    
    @abstractmethod
    def save_text(self, text: str, filename: str) -> None:
        """保存文本到文件
        
        Args:
            text: 要保存的文本
            filename: 文件名
        """
        pass
    
    @abstractmethod
    def load_text(self, filename: str) -> str:
        """从文件加载文本
        
        Args:
            filename: 文件名
            
        Returns:
            加载的文本
        """
        pass


# 归一化处理接口
class ScoreNormalizer(ABC):
    """分数归一化处理接口
    
    对原始分数进行归一化处理。
    """
    
    @abstractmethod
    def normalize(self, scores: Dict, **kwargs) -> Dict:
        """归一化分数
        
        Args:
            scores: 原始分数
            **kwargs: 其他参数，如最小值、最大值等
            
        Returns:
            归一化后的分数
        """
        pass


# 作业处理器接口 - 外观模式
class HomeworkProcessor(ABC):
    """作业处理器接口
    
    作为系统的外观，协调各个组件完成作业处理。
    """
    
    @abstractmethod
    def process_homework_directories(self) -> List[str]:
        """处理作业目录
        
        Returns:
            作业目录路径列表
        """
        pass
    
    @abstractmethod
    def process_student_answers(self, homework_data: Dict) -> None:
        """处理学生答案
        
        Args:
            homework_data: 作业数据
        """
        pass
    
    @abstractmethod
    def generate_grading_standard(self, homework_data: Dict, number_prepare: int) -> str:
        """生成评分标准
        
        Args:
            homework_data: 作业数据
            number_prepare: 准备的样本数量
            
        Returns:
            生成的评分标准
        """
        pass
    
    @abstractmethod
    def grade_homework(self, homework_data: Dict, grading_standard: str, number_gen: int) -> None:
        """批改作业
        
        Args:
            homework_data: 作业数据
            grading_standard: 评分标准
            number_gen: 生成的样本数量
        """
        pass
    
    @abstractmethod
    def save_results(self, normalize: bool = False) -> None:
        """保存结果
        
        Args:
            normalize: 是否对分数进行归一化处理
        """
        pass
    
    @abstractmethod
    def run(self) -> None:
        """运行作业处理流程"""
        pass


# 图片处理接口
class ImageProcessor(ABC):
    """图片处理接口
    
    处理图片下载和转换。
    """
    
    @abstractmethod
    def download_image(self, url: str) -> Optional[str]:
        """下载图片并转换为Base64编码
        
        Args:
            url: 图片URL
            
        Returns:
            Base64编码的图片数据，如果下载失败则返回None
        """
        pass


# 作业批改器工厂接口
class HomeworkGraderFactory(ABC):
    """作业批改器工厂接口
    
    创建作业批改器实例。
    """
    
    @abstractmethod
    def create_grader(self, api_key: str, base_url: str) -> 'HomeworkGrader':
        """创建作业批改器
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
            
        Returns:
            作业批改器实例
        """
        pass


# 作业批改器接口
class HomeworkGrader(ABC):
    """作业批改器接口
    
    定义作业批改器的核心功能。
    """
    
    @abstractmethod
    def create_messages_with_images(self, homework_data: Dict, student_name: str) -> List[Dict]:
        """创建包含图片的消息列表
        
        Args:
            homework_data: 作业数据
            student_name: 学生姓名
            
        Returns:
            包含学生答案和图片的消息列表
        """
        pass
    
    @abstractmethod
    def gen_prepare_system_prompt(self, homework_data: Dict, number: int) -> List[Dict]:
        """生成系统提示信息
        
        Args:
            homework_data: 作业数据
            number: 需要处理的题目数量
            
        Returns:
            包含系统提示信息的消息列表
        """
        pass
    
    @abstractmethod
    def gen_few_shot_learning_system_prompt(self, homework_data: Dict, grading_standard: str) -> List[Dict]:
        """生成少样本学习系统提示
        
        Args:
            homework_data: 作业数据
            grading_standard: 评分标准
            
        Returns:
            包含系统提示信息的消息列表
        """
        pass
    
    @abstractmethod
    def prepare_score(self, prepare_system_prompt: List[Dict], number: int) -> Tuple[str, List[str]]:
        """准备参考分数和评分标准
        
        Args:
            prepare_system_prompt: 准备阶段的系统提示
            number: 需要处理的答案数量
            
        Returns:
            生成的评分标准和选定的学生键列表
        """
        pass
    
    @abstractmethod
    def gen_score(self, number_gen: int, selected_dict_uncorrected: Dict, few_shot_learning_system_prompt: List[Dict]) -> None:
        """生成学生分数
        
        Args:
            number_gen: 用于参考的样本数量
            selected_dict_uncorrected: 选定的未批改答案
            few_shot_learning_system_prompt: 少样本学习系统提示
        """
        pass
    
    @abstractmethod
    def normalize_score(self, student_scores: Dict, **kwargs) -> Dict:
        """对学生成绩进行归一化处理
        
        Args:
            student_scores: 包含学生最终成绩的字典
            **kwargs: 其他参数，如最小值、最大值等
            
        Returns:
            归一化处理后的成绩字典
        """
        pass
    
    @abstractmethod
    def save_grades(self, scores_to_save: Dict) -> None:
        """将成绩保存到Excel文件
        
        Args:
            scores_to_save: 归一化处理后的成绩字典
        """
        pass
    
    @abstractmethod
    def run(self) -> None:
        """批改作业的主要流程"""
        pass