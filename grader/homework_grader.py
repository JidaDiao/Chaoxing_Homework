from typing import Dict, List, Tuple, Optional
from grader.interfaces import HomeworkGrader, AIService, FileStorage, ImageProcessor, ScoreNormalizer, MessageFactory
import os
import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor
import glob
import xlrd
from xlutils.copy import copy
from config.args import config


class DefaultHomeworkGrader(HomeworkGrader):
    """默认作业批改器实现
    
    实现作业批改器的核心功能，包括创建消息、生成系统提示、准备评分标准和生成分数等。
    """
    
    def __init__(self, ai_service: AIService, file_storage: FileStorage, 
                 image_processor: ImageProcessor, score_normalizer: ScoreNormalizer,
                 message_factory: MessageFactory):
        """初始化作业批改器
        
        Args:
            ai_service: AI服务实例
            file_storage: 文件存储实例
            image_processor: 图片处理器实例
            score_normalizer: 分数归一化处理器实例
            message_factory: 消息工厂实例
        """
        self.ai_service = ai_service
        self.file_storage = file_storage
        self.image_processor = image_processor
        self.score_normalizer = score_normalizer
        self.message_factory = message_factory
        self.student_answers_prompt_uncorrected = {}
        self.student_answers_prompt_corrected = {}
        self.student_score_final = {}
    
    def create_messages_with_images(self, homework_data: Dict, student_name: str) -> List[Dict]:
        """创建包含图片的消息列表
        
        Args:
            homework_data: 作业数据
            student_name: 学生姓名
            
        Returns:
            包含学生答案和图片的消息列表
        """
        student_answers_list = []
        user_prompt = student_name + "：\n"
        student_answers = homework_data["学生回答"][student_name]
        
        for _, (a_key, a_value) in enumerate(student_answers.items(), 1):
            if len(a_value["text"]) == 0:
                user_prompt += a_key + "：" + "" + "\n"
            else:
                user_prompt += a_key + "：" + a_value["text"][0] + "\n"
            
            for img_url in a_value["images"]:
                img_base64 = self.image_processor.download_image(img_url)
                if img_base64:
                    student_answers_list.append(self.message_factory.create_image_message(img_base64))
        
        student_answers_list.append(self.message_factory.create_user_message(user_prompt))
        logging.info(f"正在为学生 {student_name} 创建消息")
        return student_answers_list
    
    def gen_prepare_system_prompt(self, homework_data: Dict, number: int) -> List[Dict]:
        """生成系统提示信息
        
        Args:
            homework_data: 作业数据
            number: 需要处理的题目数量
            
        Returns:
            包含系统提示信息的消息列表
        """
        question_stem = "###\n"
        for _, (key, value) in enumerate(homework_data["题目"].items(), start=1):
            question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

        system_prompt = config.prepare_system_prompt.format(
            question_stem=question_stem,
            number=str(number),
            number_=str(number-1)
        )
        
        return [self.message_factory.create_system_message(system_prompt)]
    
    def gen_few_shot_learning_system_prompt(self, homework_data: Dict, grading_standard: str) -> List[Dict]:
        """生成少样本学习系统提示
        
        Args:
            homework_data: 作业数据
            grading_standard: 评分标准
            
        Returns:
            包含系统提示信息的消息列表
        """
        question_stem = "###\n"
        for _, (key, value) in enumerate(homework_data["题目"].items(), start=1):
            question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

        system_prompt = config.few_shot_learning_system_prompt.format(
            question_stem=question_stem,
            grading_standard=grading_standard
        )
        
        return [self.message_factory.create_system_message(system_prompt)]
    
    def prepare_score(self, prepare_system_prompt: List[Dict], number: int) -> Tuple[str, List[str]]:
        """准备参考分数和评分标准
        
        Args:
            prepare_system_prompt: 准备阶段的系统提示
            number: 需要处理的答案数量
            
        Returns:
            生成的评分标准和选定的学生键列表
        """
        # 随机选择未批改的学生答案
        selected_keys = random.sample(list(self.student_answers_prompt_uncorrected.keys()), number)
        selected_dict_uncorrected = {key: self.student_answers_prompt_uncorrected[key] for key in selected_keys}
        
        # 准备上下文提示信息
        context_prompt = prepare_system_prompt.copy()
        for index, (key, value) in enumerate(selected_dict_uncorrected.items(), start=1):
            context_prompt.extend(value)
            if index < (number-1):
                context_prompt.append({
                    "role": "assistant",
                    "content": f"第{index}轮：pass"
                })
            if index == (number-1):
                context_prompt.append({
                    "role": "assistant",
                    "content": f"第{index}轮：pass，下一次回复我将对所有学生进行打分，并提供打分依据和评分标准。"
                })
        
        # 使用AI服务生成评分结果
        response = self.ai_service.generate_completion(context_prompt)
        response_content = self.ai_service.extract_json_from_response(response)
        
        count = 1
        while response_content is None or len(response_content['student_scores']) != number or response_content['grading_standard'] == "":
            self.student_score_final = {}
            selected_keys = random.sample(list(self.student_answers_prompt_uncorrected.keys()), number)
            selected_dict_uncorrected = {key: self.student_answers_prompt_uncorrected[key] for key in selected_keys}
            
            context_prompt = prepare_system_prompt.copy()
            for index, (key, value) in enumerate(selected_dict_uncorrected.items(), start=1):
                context_prompt.extend(value)
                if index < (number-1):
                    context_prompt.append({
                        "role": "assistant",
                        "content": f"第{index}轮：pass"
                    })
                if index == (number-1):
                    context_prompt.append({
                        "role": "assistant",
                        "content": f"第{index}轮：pass，下一次回复我将对所有学生进行打分，并提供打分依据和评分标准。"
                    })
            
            response = self.ai_service.generate_completion(context_prompt)
            response_content = self.ai_service.extract_json_from_response(response)
            
            count += 1
            if count % 2 == 0 and number > config.number_prepare_min:
                number -= 1
        
        # 处理评分结果
        student_scores = response_content['student_scores']
        grading_standard = response_content['grading_standard']
        
        # 保存学生分数
        for _, (key, value) in enumerate(student_scores.items()):
            self.student_score_final[key] = value
        
        self.file_storage.save_json(self.student_score_final, "original_student_score.json")
        
        # 更新已批改的学生答案
        for _, (key, value) in enumerate(selected_dict_uncorrected.items()):
            try:
                value_ = value.copy()
                value_.append({
                    "role": "assistant",
                    "content": str({key: student_scores[key]}),
                })
                self.student_answers_prompt_corrected[key] = value_
            except Exception as e:
                logging.error(f"发生错误: {str(e)}")
        
        logging.info("准备参考分数和评分标准")
        return grading_standard, selected_keys
    
    def gen_score(self, number_gen: int, selected_dict_uncorrected: Dict, few_shot_learning_system_prompt: List[Dict]) -> None:
        """生成学生分数
        
        Args:
            number_gen: 用于参考的样本数量
            selected_dict_uncorrected: 选定的未批改答案
            few_shot_learning_system_prompt: 少样本学习系统提示
        """
        # 随机选择已批改的学生答案作为参考
        selected_keys = random.sample(list(self.student_answers_prompt_corrected.keys()), number_gen)
        selected_dict_corrected = {key: self.student_answers_prompt_corrected[key] for key in selected_keys}
        
        # 准备上下文提示信息
        context_prompt = few_shot_learning_system_prompt.copy()
        
        # 添加已批改的样本作为参考
        for key, value in selected_dict_corrected.items():
            context_prompt.extend(value)
        
        # 添加待批改的样本
        for key, value in selected_dict_uncorrected.items():
            context_prompt.extend(value)
        
        # 使用AI服务生成评分结果
        response = self.ai_service.generate_completion(context_prompt)
        response_content = self.ai_service.extract_json_from_response(response)
        
        student_scores = response_content.get('student_scores', None) if response_content else None
        
        count = 1
        while student_scores is None:
            # 大模型打分出错了，需要重新生成
            selected_keys = random.sample(list(self.student_answers_prompt_corrected.keys()), number_gen)
            selected_dict_corrected = {key: self.student_answers_prompt_corrected[key] for key in selected_keys}
            
            context_prompt = few_shot_learning_system_prompt.copy()
            for key, value in selected_dict_corrected.items():
                context_prompt.extend(value)
            for key, value in selected_dict_uncorrected.items():
                context_prompt.extend(value)
            
            response = self.ai_service.generate_completion(context_prompt)
            response_content = self.ai_service.extract_json_from_response(response)
            student_scores = response_content.get('student_scores', None) if response_content else None
            
            count += 1
            if count % 2 == 0 and number_gen > config.number_gen_min:
                number_gen -= 1  # 可能是参考样本太多了导致提示词过长了
        
        # 保存学生分数
        for _, (key, value) in enumerate(student_scores.items()):
            self.student_score_final[key] = value
        
        self.file_storage.save_json(self.student_score_final, "original_student_score.json")
        
        # 更新已批改的学生答案
        for _, (key, value) in enumerate(selected_dict_uncorrected.items()):
            try:
                value_ = value.copy()
                value_.append({
                    "role": "assistant",
                    "content": str({key: student_scores[key]}),
                })
                self.student_answers_prompt_corrected[key] = value_
            except Exception as e:
                logging.error(f"发生错误: {str(e)}")
    
    def normalize_score(self, student_scores: Dict, **kwargs) -> Dict:
        """对学生成绩进行归一化处理
        
        Args:
            student_scores: 包含学生最终成绩的字典
            **kwargs: 其他参数，如最小值、最大值等
            
        Returns:
            归一化处理后的成绩字典
        """
        return self.score_normalizer.normalize(student_scores, **kwargs)
    
    def save_grades(self, scores_to_save: Dict) -> None:
        """将成绩保存到Excel文件
        
        Args:
            scores_to_save: 归一化处理后的成绩字典
        """
        xls_file = glob.glob("*.xls")[0]
        workbook = xlrd.open_workbook(xls_file, formatting_info=True)
        sheet = workbook.sheet_by_index(0)

        student_name_col_idx = None
        score_col_idx = None

        for col in range(sheet.ncols):
            header = sheet.cell_value(1, col)
            if "学生姓名" in header:
                student_name_col_idx = col
            elif "分数" in header:
                score_col_idx = col

        if student_name_col_idx is None or score_col_idx is None:
            logging.error("未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")
            raise ValueError("未找到'学生姓名'或'分数'列，请