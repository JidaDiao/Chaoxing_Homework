import os
import logging
from typing import Dict, List, Any

from .interface import IHomeworkGrader
from .file_manager import FileManager
from .score_processor_v2 import ScoreProcessorV2, GradingError
from .message_builder import MessageBuilder
from .homework_processor import HomeworkProcessor
from .llm_client import LLMClient
from utils import randomselect_uncorrected


class HomeworkGrader(IHomeworkGrader):
    """作业批改器类，用于自动批改学生作业

    该类实现了IHomeworkGrader接口，作为协调者使用其他专门的类来完成作业批改工作。
    整合了作业批改的所有功能，包括导入作业数据、处理学生答案、生成评分标准、
    批改作业和保存结果。

    Attributes:
        llm_client (LLMClient): Responses API客户端实例
        file_manager (FileManager): 文件管理器实例
        message_builder (MessageBuilder): 消息构建器实例
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
        self.llm_client = LLMClient(
            api_key=config.api_key,
            base_url=config.base_url,
            default_model=config.prepare_model,
        )
        self.file_manager = FileManager()
        self.message_builder = MessageBuilder(
            prepare_system_prompt=config.prepare_system_prompt,
            few_shot_learning_system_prompt=config.few_shot_learning_system_prompt
        )

        # 初始化 HomeworkProcessor
        self.homework_processor = HomeworkProcessor()

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

                score_processor = ScoreProcessorV2(
                    llm_client=self.llm_client,
                    prepare_model=self.config.prepare_model,
                    gen_model=self.config.gen_model,
                    batch_size=self._resolve_batch_size(),
                    on_score_update=self._save_score_callback,
                )
                score_processor.set_student_answers(
                    uncorrected=student_answers_prompt_uncorrected,
                    corrected=student_answers_prompt_corrected,
                    final_scores=student_score_final,
                    grading_standard=grading_standard,
                )

                homework_id = self._resolve_homework_id(homework_dir, homework_data)
                score_processor.initialize_context(homework_data, homework_id)

                # 3. 生成评分标准（或恢复已有标准）
                if grading_standard:
                    try:
                        score_processor.attach_grading_standard(grading_standard)
                    except Exception as exc:
                        logging.error("Attach grading standard failed, will regenerate: %s", exc)
                        grading_standard = None

                if not grading_standard:
                    sample_number = self._resolve_sample_size(
                        len(student_answers_prompt_uncorrected)
                    )
                    if sample_number <= 0:
                        logging.error("Sample size unavailable, skip homework: %s", homework_id)
                        continue

                    sample_students, sample_keys = randomselect_uncorrected(
                        student_answers_prompt_uncorrected, sample_number
                    )
                    grading_standard = score_processor.generate_grading_standard(
                        sample_students, sample_number
                    )
                    self.file_manager.save_grading_standard(grading_standard)
                    score_processor.remove_uncorrected(sample_keys)

                    self.file_manager.save_score_results(
                        score_processor.get_final_scores(),
                        "original_student_score.json",
                    )

                # 4. 批改剩余作业并生成分数
                self._grade_remaining_homework(score_processor)

                # 5. 保存结果
                self._save_results(score_processor)
        except Exception as e:
            logging.error(f"作业批改过程中发生错误: {str(e)}")
            # 可以添加适当的清理代码

    def _resolve_homework_id(self, homework_dir: str, homework_data: Dict[str, Any]) -> str:
        homework_id = None
        if isinstance(homework_data, dict):
            for key in ("作业ID", "homework_id", "id"):
                if key in homework_data:
                    homework_id = homework_data.get(key)
                    break
        return str(homework_id) if homework_id else os.path.basename(homework_dir)

    def _resolve_sample_size(self, available: int) -> int:
        if available <= 0:
            return 0
        max_sample = min(max(self.config.number_prepare_max, 5), 8)
        sample_size = min(available, max_sample)
        if sample_size < 5:
            logging.warning("样本数量不足 5，当前仅有 %s 份", sample_size)
        return sample_size

    def _resolve_batch_size(self) -> int:
        return max(3, min(5, self.config.number_gen_max))


    def _save_score_callback(self, current_scores: Dict[str, Any], updated_students: List[str]) -> None:
        """分数保存回调函数

        Args:
            current_scores: 当前所有学生分数
            updated_students: 本次更新的学生列表
        """
        try:
            self.file_manager.save_score_results(
                current_scores,
                "original_student_score.json",
            )
            logging.info("已保存学生 %s 的分数到文件", updated_students)
        except Exception as e:
            logging.error("保存分数文件时出错: %s", str(e))

    def _grade_remaining_homework(self, score_processor: ScoreProcessorV2) -> None:
        """批改剩余的作业"""
        student_answers_prompt_uncorrected = score_processor.get_uncorrected_answers()
        if not student_answers_prompt_uncorrected:
            return

        try:
            score_processor.grade_students_batch(student_answers_prompt_uncorrected)
        except GradingError as exc:
            logging.error("Batch grading failed: %s", exc)


    def _save_results(self, score_processor: ScoreProcessorV2) -> None:
        """保存批改结果

        将最终分数保存到文件中，并根据配置决定是否进行分数归一化。
        """
        student_score_final = score_processor.get_final_scores()

        # 提取分数
        student_score_to_save = {}
        for _, (key, value) in enumerate(student_score_final.items()):
            student_score_to_save[key] = value['score']

        # 是否需要归一化分数
        if self.config.pulling_students_up:
            normalized_scores = score_processor.normalize_score(
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
        self.file_manager.save_score_results(
            student_score_final,
            "original_student_score.json",
        )
