import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

from .interface import IHomeworkGrader
from .file_manager import FileManager
from .score_processor import ScoreProcessor
from .message_builder import MessageBuilder
from .homework_processor import HomeworkProcessor
from .openai_client import OpenAIClient


class HomeworkGrader(IHomeworkGrader):
    """作业批改器类，用于自动批改学生作业

    该类实现了IHomeworkGrader接口，作为协调者使用其他专门的类来完成作业批改工作。
    整合了作业批改的所有功能，包括导入作业数据、处理学生答案、生成评分标准、
    批改作业和保存结果。

    Attributes:
        ai_client (OpenAIClient): OpenAI API客户端实例
        file_manager (FileManager): 文件管理器实例
        message_builder (MessageBuilder): 消息构建器实例
        score_processor (ScoreProcessor): 分数处理器实例
        homework_processor (HomeworkProcessor): 作业处理器实例
        config (Dict): 配置参数
    """

    def __init__(self, config: Any):
        """初始化作业批改器

        Args:
            config: 配置参数对象，通常是argparse.Namespace类型
        """
        # 配置日志
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        logging.getLogger("openai").setLevel(logging.ERROR)

        # 直接使用config对象，不需要转换为字典
        self.config = config

        # 创建各组件实例
        self.ai_client = OpenAIClient(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self.file_manager = FileManager()
        self.message_builder = MessageBuilder(
            prepare_system_prompt=config.prepare_system_prompt,
            few_shot_learning_system_prompt=config.few_shot_learning_system_prompt
        )
        self.score_processor = ScoreProcessor(
            ai_client=self.ai_client,
            prepare_model=config.prepare_model,
            gen_model=config.gen_model,
            number_prepare_min=config.number_prepare_min,
            number_gen_min=config.number_gen_min
        )
        self.homework_processor = HomeworkProcessor(
            max_workers=config.max_workers
        )

    def run(self) -> None:
        """运行作业批改流程

        协调各个组件完成作业批改的完整流程，包括：
        1. 导入作业数据
        2. 处理学生答案
        3. 生成评分标准
        4. 批改作业并生成分数
        5. 保存结果
        """
        try:
            # 获取所有需要批改的作业目录
            homework_dirs = self.homework_processor.process_homework_directories()

            for homework_dir in homework_dirs:
                os.chdir(homework_dir)
                logging.info(f"当前正在改: {os.getcwd()}")

                # 1. 导入作业数据
                homework_data = self.file_manager.import_json_file(
                    "./answer.json")

                # 2. 处理学生答案
                student_answers_prompt_uncorrected = self.homework_processor.process_student_answers(
                    homework_data, self.message_builder
                )

                # 检查是否有已存在的评分
                (
                    student_answers_prompt_uncorrected,
                    student_answers_prompt_corrected,
                    student_score_final,
                    grading_standard
                ) = self.homework_processor.process_existing_scores(student_answers_prompt_uncorrected)

                # 如果所有学生都已评分，跳过当前作业
                if not student_answers_prompt_uncorrected:
                    continue

                # 设置score_processor的数据
                self.score_processor.set_student_answers(
                    uncorrected=student_answers_prompt_uncorrected,
                    corrected=student_answers_prompt_corrected,
                    final_scores=student_score_final
                )

                number_prepare = self.config.number_prepare_max
                number_gen = self.config.number_gen_max

                # 3. 生成评分标准（如果没有已存在的）
                if not grading_standard:
                    prepare_system_prompt = self.message_builder.gen_prepare_system_prompt(
                        homework_data, number_prepare
                    )

                    grading_standard = self.score_processor.prepare_score(
                        prepare_system_prompt, number_prepare
                    )
                    self.file_manager.save_grading_standard(grading_standard)

                    # 保存初步评分结果
                    self.file_manager.save_json_file(
                        self.score_processor.get_final_scores(),
                        "original_student_score.json"
                    )

                # 4. 批改剩余作业并生成分数
                self._grade_remaining_homework(
                    homework_data, grading_standard, number_gen)

                # 5. 保存结果
                self._save_results()
        except Exception as e:
            logging.error(f"作业批改过程中发生错误: {str(e)}")
            # 可以添加适当的清理代码

    def _grade_remaining_homework(self, homework_data: Dict[str, Any],
                                  grading_standard: str, number_gen: int) -> None:
        """批改剩余的作业

        使用生成的评分标准批改剩余未评分的学生作业。

        Args:
            homework_data: 作业数据
            grading_standard: 评分标准
            number_gen: 生成分数时使用的参考样本数量
        """
        # 获取未批改的学生答案
        student_answers_prompt_uncorrected = self.score_processor.get_uncorrected_answers()
        few_shot_learning_system_prompt = self.message_builder.gen_few_shot_learning_system_prompt(
                    homework_data, grading_standard
                )
        # for _, (student_name, student_answer) in enumerate(student_answers_prompt_uncorrected.items()):                
        #     selected_dict_uncorrected = {student_name: student_answer}
        #     self.score_processor.gen_score(
        #                 number_gen,
        #                 selected_dict_uncorrected,
        #                 few_shot_learning_system_prompt,)

        # 使用线程池并行批改作业
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            for _, (student_name, student_answer) in enumerate(student_answers_prompt_uncorrected.items()):                
                selected_dict_uncorrected = {student_name: student_answer}
                executor.submit(
                    self.score_processor.gen_score,
                    number_gen,
                    selected_dict_uncorrected,
                    few_shot_learning_system_prompt,
                )

                # 保存原始评分结果
        self.file_manager.save_json_file(
            self.score_processor.get_final_scores(),
            "original_student_score.json"
        )

    def _save_results(self) -> None:
        """保存批改结果

        将最终分数保存到文件中，并根据配置决定是否进行分数归一化。
        """
        student_score_final = self.score_processor.get_final_scores()

        # 提取分数
        student_score_to_save = {}
        for _, (key, value) in enumerate(student_score_final.items()):
            student_score_to_save[key] = value['score']

        # 是否需要归一化分数
        if self.config.pulling_students_up:
            normalized_scores = self.score_processor.normalize_score(
                student_score_to_save,
                normalized_min=self.config.normalized_min,
                normalized_max=self.config.normalized_max,
                original_min=self.config.original_min,
                original_max=self.config.original_max,
            )
            self.file_manager.save_grades(normalized_scores)

            # 保存归一化后的分数
            self.file_manager.save_json_file(
                normalized_scores,
                "normalized_student_score.json"
            )
        else:
            # 直接保存原始分数
            self.file_manager.save_grades(student_score_to_save)

        # 保存原始评分结果
        self.file_manager.save_json_file(
            student_score_final,
            "original_student_score.json"
        )