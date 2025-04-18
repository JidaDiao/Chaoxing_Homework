import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from .interface import IHomeworkProcessor, IMessageBuilder
from utils.tools import my_lisdir


class HomeworkProcessor(IHomeworkProcessor):
    """作业处理器类，负责处理作业目录和学生答案

    该类实现了IHomeworkProcessor接口，提供了处理作业目录和学生答案的功能。

    Attributes:
        max_workers (int): 线程池最大工作线程数
    """

    def __init__(self, max_workers: int = 5):
        """初始化作业处理器

        Args:
            max_workers: 线程池最大工作线程数，默认为5
        """
        self.max_workers = max_workers

    @staticmethod
    def process_homework_directories() -> List[str]:
        """处理作业目录

        遍历homework目录，获取所有需要批改的作业目录路径。

        Returns:
            作业目录路径列表
        """
        class_list = my_lisdir('homework')
        homework_dirs = []

        for class_name in class_list:
            homework_names = my_lisdir(os.path.join('homework', class_name))
            for homework_name in homework_names:
                homework_dirs.append(
                    os.path.join(os.getcwd(), 'homework',
                                 class_name, homework_name)
                )
        return homework_dirs

    @staticmethod
    def process_student_answers(homework_data: Dict[str, Any],
                                message_builder: IMessageBuilder) -> Dict[str, List[Dict[str, Any]]]:
        """处理学生答案

        处理学生答案数据，使用MessageBuilder创建包含图片的消息列表。

        Args:
            homework_data: 作业数据
            message_builder: 消息构建器实例

        Returns:
            处理后的学生答案
        """
        student_answers_prompt = {}

        # 检查是否已存在处理好的答案文件
        if os.path.exists("./student_answers_prompt.json"):
            with open("./student_answers_prompt.json", "r", encoding="utf-8") as file:
                student_answers_prompt = json.load(file)
            logging.info("已加载现有的学生答案数据")
            return student_answers_prompt

        # 创建线程安全的字典
        dict_lock = Lock()

        # 并行处理学生答案
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures_to_names = {}
            
            # 提交所有任务
            for student_name in homework_data["学生回答"].keys():
                future = executor.submit(
                    message_builder.create_student_messages_with_images, homework_data, student_name
                )
                futures_to_names[future] = student_name
            
            # 收集结果并处理错误
            for future in as_completed(futures_to_names):
                student_name = futures_to_names[future]
                try:
                    result = future.result()
                    with dict_lock:
                        student_answers_prompt[student_name] = result
                    logging.info(f"成功处理学生 {student_name} 的答案")
                except Exception as exc:
                    logging.error(f"处理学生 {student_name} 的答案时出错: {exc}")

        # 保存处理结果
        with open("student_answers_prompt.json", "w", encoding="utf-8") as json_file:
            json.dump(
                student_answers_prompt,
                json_file,
                indent=4,
                sort_keys=True,
                ensure_ascii=False,
            )

        logging.info("已完成所有学生答案的处理")
        return student_answers_prompt

    def process_existing_scores(self, student_answers_prompt_uncorrected: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]], Dict[str, Any], Optional[str]]:
        """处理已存在的分数

        如果存在原始分数文件，则处理已批改和未批改的答案。

        Args:
            student_answers_prompt_uncorrected: 未批改的学生答案

        Returns:
            Tuple包含:
            - 更新后的未批改答案
            - 已批改答案
            - 最终分数
            - 评分标准（如果存在）
        """
        student_answers_prompt_corrected = {}
        student_score_final = {}
        grading_standard = None

        if os.path.exists("original_student_score.json"):
            # 加载已存在的分数
            with open("original_student_score.json", "r", encoding="utf-8") as file:
                student_score_final = json.load(file)

            # 如果所有学生都已评分，则不需要继续处理
            if len(student_score_final) >= len(student_answers_prompt_uncorrected):
                logging.info("所有学生已评分完成")
                return {}, student_answers_prompt_corrected, student_score_final, None

            # 将已评分的学生答案从未批改中移到已批改中
            student_answers_prompt_corrected = {
                k: v
                for k, v in student_answers_prompt_uncorrected.items()
                if k in student_score_final
            }

            for _, (key, value) in enumerate(student_answers_prompt_corrected.items()):
                value_ = value.copy()
                value_.append({
                    "role": "assistant",
                    "content":  str({key: student_score_final[key]}),
                })
                student_answers_prompt_corrected[key] = value_
            
            student_answers_prompt_uncorrected = {
                k: v
                for k, v in student_answers_prompt_uncorrected.items()
                if k not in student_score_final
            }

            # 加载评分标准
            if os.path.exists("./评分标准.md"):
                with open("./评分标准.md", "r", encoding="utf-8") as f:
                    grading_standard = f.read()

            logging.info(
                f"已加载 {len(student_score_final)} 名学生的评分，还有 {len(student_answers_prompt_uncorrected)} 名学生需要评分")

        return student_answers_prompt_uncorrected, student_answers_prompt_corrected, student_score_final, grading_standard
