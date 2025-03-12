from typing import Dict, List
from grader.interfaces import HomeworkProcessor, FileStorage, AIService, ImageProcessor, ScoreNormalizer
import os
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from config.args import config


class DefaultHomeworkProcessor(HomeworkProcessor):
    """默认作业处理器实现
    
    作为系统的外观，协调各个组件完成作业处理。
    """
    
    def __init__(self, ai_service: AIService, file_storage: FileStorage, 
                 image_processor: ImageProcessor, score_normalizer: ScoreNormalizer):
        """初始化作业处理器
        
        Args:
            ai_service: AI服务实例
            file_storage: 文件存储实例
            image_processor: 图片处理器实例
            score_normalizer: 分数归一化处理器实例
        """
        self.ai_service = ai_service
        self.file_storage = file_storage
        self.image_processor = image_processor
        self.score_normalizer = score_normalizer
        self.student_answers_prompt_uncorrected = {}
        self.student_answers_prompt_corrected = {}
        self.student_score_final = {}
        self.homework_dirs = []
    
    def process_homework_directories(self) -> List[str]:
        """处理作业目录
        
        Returns:
            作业目录路径列表
        """
        class_list = os.listdir('homework')
        homework_dirs = []

        for class_name in class_list:
            homework_names = os.listdir(os.path.join('homework', class_name))
            for homework_name in homework_names:
                homework_dirs.append(
                    os.path.join(os.getcwd(), 'homework',
                                 class_name, homework_name)
                )
        self.homework_dirs = homework_dirs
        return homework_dirs
    
    def process_student_answers(self, homework_data: Dict) -> None:
        """处理学生答案
        
        Args:
            homework_data: 作业数据
        """
        from grader.homework_grader import DefaultHomeworkGrader
        
        if os.path.exists("./student_answers_prompt.json"):
            self.student_answers_prompt_uncorrected = self.file_storage.load_json(
                "./student_answers_prompt.json"
            )
        else:
            # 创建一个临时的HomeworkGrader实例来处理学生答案
            temp_grader = DefaultHomeworkGrader(
                ai_service=self.ai_service,
                file_storage=self.file_storage,
                image_processor=self.image_processor,
                score_normalizer=self.score_normalizer,
                message_factory=None  # 这里需要传入MessageFactory实例
            )
            
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(
                        temp_grader.create_messages_with_images, homework_data, student_name
                    ): student_name
                    for student_name in homework_data["学生回答"].keys()
                }
                
                for future in futures:
                    student_name = futures[future]
                    self.student_answers_prompt_uncorrected[student_name] = future.result()
                    
            self.file_storage.save_json(
                self.student_answers_prompt_uncorrected,
                "student_answers_prompt.json"
            )
    
    def generate_grading_standard(self, homework_data: Dict, number_prepare: int) -> str:
        """生成评分标准
        
        Args:
            homework_data: 作业数据
            number_prepare: 准备的样本数量
            
        Returns:
            生成的评分标准
        """
        from grader.homework_grader import DefaultHomeworkGrader
        from grader.message_factory import OpenAIMessageFactory
        
        # 创建一个临时的HomeworkGrader实例来生成评分标准
        message_factory = OpenAIMessageFactory()
        temp_grader = DefaultHomeworkGrader(
            ai_service=self.ai_service,
            file_storage=self.file_storage,
            image_processor=self.image_processor,
            score_normalizer=self.score_normalizer,
            message_factory=message_factory
        )
        
        # 处理已存在的分数
        if os.path.exists("original_student_score.json"):
            self.student_score_final = self.file_storage.load_json(
                "./original_student_score.json")
            if len(self.student_score_final) >= len(self.student_answers_prompt_uncorrected):
                return None

            self.student_answers_prompt_corrected = {
                k: v
                for k, v in self.student_answers_prompt_uncorrected.items()
                if k in self.student_score_final
            }
            for _, (key, value) in enumerate(self.student_answers_prompt_corrected.items()):
                value_ = value.copy()
                value_.append({
                    "role": "assistant",
                    "content":  str(self.student_score_final[key]),
                })
                self.student_answers_prompt_corrected[key] = value_

            self.student_answers_prompt_uncorrected = {
                k: v
                for k, v in self.student_answers_prompt_uncorrected.items()
                if k not in self.student_score_final
            }

            with open("./评分标准.md", "r", encoding="utf-8") as f:
                grading_standard = f.read()
            return grading_standard
        
        # 生成新的评分标准
        self.student_answers_prompt_corrected = {}
        self.student_score_final = {}
        
        prepare_system_prompt = temp_grader.gen_prepare_system_prompt(
            homework_data, number_prepare)
        grading_standard, selected_keys = temp_grader.prepare_score(
            prepare_system_prompt, number_prepare)
        
        # 从未批改的答案中移除已选择的键
        for key in selected_keys:
            self.student_answers_prompt_uncorrected.pop(key, None)
            
        self.file_storage.save_text(grading_standard, "评分标准.md")
        
        return grading_standard
    
    def grade_homework(self, homework_data: Dict, grading_standard: str, number_gen: int) -> None:
        """批改作业
        
        Args:
            homework_data: 作业数据
            grading_standard: 评分标准
            number_gen: 生成的样本数量
        """
        from grader.homework_grader import DefaultHomeworkGrader
        from grader.message_factory import OpenAIMessageFactory
        
        message_factory = OpenAIMessageFactory()
        temp_grader = DefaultHomeworkGrader(
            ai_service=self.ai_service,
            file_storage=self.file_storage,
            image_processor=self.image_processor,
            score_normalizer=self.score_normalizer,
            message_factory=message_factory
        )
        
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            for _, (student_name, student_answer) in enumerate(
                self.student_answers_prompt_uncorrected.items()
            ):
                few_shot_learning_system_prompt = temp_grader.gen_few_shot_learning_system_prompt(
                    homework_data, grading_standard
                )
                selected_dict_uncorrected = {student_name: student_answer}
                executor.submit(
                    temp_grader.gen_score,
                    number_gen,
                    selected_dict_uncorrected,
                    few_shot_learning_system_prompt,
                )
    
    def save_results(self, normalize: bool = False) -> None:
        """保存结果
        
        Args:
            normalize: 是否对分数进行归一化处理
        """
        from grader.homework_grader import DefaultHomeworkGrader
        from grader.message_factory import OpenAIMessageFactory
        
        message_factory = OpenAIMessageFactory()
        temp_grader = DefaultHomeworkGrader(
            ai_service=self.ai_service,
            file_storage=self.file_storage,
            image_processor=self.image_processor,
            score_normalizer=self.score_normalizer,
            message_factory=message_factory
        )
        
        student_score_to_save = {}
        for _, (key, value) in enumerate(self.student_score_final.items()):
            student_score_to_save[key] = value['score']
            
        if normalize:
            normalized_scores = temp_grader.normalize_score(
                student_score_to_save,
                normalized_min=config.normalized_min,
                normalized_max=config.normalized_max,
                original_min=config.original_min,
                original_max=config.original_max,
            )
            temp_grader.save_grades(normalized_scores)
            
            self.file_storage.save_json(
                normalized_scores,
                "normalized_student_score.json"
            )
        else:
            temp_grader.save_grades(student_score_to_save)
    
    def run(self) -> None:
        """运行作业处理流程"""
        homework_dirs = self.process_homework_directories()
        
        for homework_dir in homework_dirs:
            os.chdir(homework_dir)
            logging.info(f"当前正在改: {os.getcwd()}")
            
            homework_data = self.file_storage.load_json("./answer.json")
            self.process_student_answers(homework_data)
            
            number_prepare = config.number_prepare_max
            number_gen = config.number_gen_max
            
            grading_standard = self.generate_grading_standard(homework_data, number_prepare)
            if not grading_standard:
                continue
                
            self.grade_homework(homework_data, grading_standard, number_gen)
            self.save_results(normalize=config.pulling_students_up)