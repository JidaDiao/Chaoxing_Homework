import re
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from .interface import IScoreProcessor, IOpenAIClient
from utils import randomselect_uncorrected, randompop_corrected, context_few_shot_learning_prompt, pop_uncorrected
from threading import Lock


class ScoreProcessor(IScoreProcessor):
    """分数处理器类，负责处理和管理分数相关的操作

    该类实现了IScoreProcessor接口，提供了准备参考分数和评分标准、
    生成学生分数和对学生成绩进行归一化处理的功能。

    Attributes:
        ai_client (IOpenAIClient): OpenAI客户端实例
        student_answers_prompt_uncorrected (dict): 存储未批改的学生答案
        student_answers_prompt_corrected (dict): 存储已批改的学生答案
        student_score_final (dict): 存储学生最终分数
        prepare_model (str): 用于准备阶段的模型名称
        gen_model (str): 用于生成分数的模型名称
        number_prepare_min (int): 准备阶段的最小样本数量
        number_gen_min (int): 生成分数阶段的最小样本数量
        lock (threading.Lock): 用于线程同步的锁
    """

    def __init__(self, ai_client: IOpenAIClient,
                 prepare_model: str,
                 gen_model: str,
                 number_prepare_min: int = 3,
                 number_gen_min: int = 2,
                 score_callback=None):  # 新增回调参数
        """初始化分数处理器

        Args:
            ai_client: OpenAI客户端实例
            prepare_model: 用于准备阶段的模型名称
            gen_model: 用于生成分数的模型名称
            number_prepare_min: 准备阶段的最小样本数量
            number_gen_min: 生成分数阶段的最小样本数量
        """
        self.ai_client = ai_client
        self.student_answers_prompt_uncorrected = {}
        self.student_answers_prompt_corrected = {}
        self.student_score_final = {}
        self.prepare_model = prepare_model
        self.gen_model = gen_model
        self.number_prepare_min = number_prepare_min
        self.number_gen_min = number_gen_min
        self.lock = Lock()
        self.score_callback = score_callback

    def set_student_answers(self, uncorrected: Dict[str, List[Dict[str, Any]]],
                            corrected: Optional[Dict[str,
                                                     List[Dict[str, Any]]]] = None,
                            final_scores: Optional[Dict[str, Any]] = None):
        """设置学生答案数据

        Args:
            uncorrected: 未批改的学生答案
            corrected: 已批改的学生答案，默认为None
            final_scores: 最终分数，默认为None
        """
        self.student_answers_prompt_uncorrected = uncorrected
        if corrected:
            self.student_answers_prompt_corrected = corrected
        if final_scores:
            self.student_score_final = final_scores

    def context_prepare_prompt(self, selected_answers, system_prompt, num_answers):
        """
        准备上下文提示信息。

        :param selected_answers: 选择的学生答案字典
        :param system_prompt: 系统提示信息
        :param num_answers: 答案数量
        :return: 准备好的上下文提示信息
        """
        context_prompt = system_prompt.copy()
        for index, (key, value) in enumerate(selected_answers.items(), start=1):
            context_prompt += value
            if index < (num_answers-1):
                context_prompt.append({
                    "role": "assistant",
                    "content": f"第{index}轮：pass"
                })
            if index == (num_answers-1):
                context_prompt.append({
                    "role": "assistant",
                    "content": f"第{index}轮：pass，下一次回复我将对所有学生进行打分，并提供打分依据和评分标准。"
                })
        logging.info('准备上下文提示信息')
        return context_prompt

    def prepare_score(self, prepare_system_prompt: List[Dict[str, str]], number: int) -> Tuple[str, List[str]]:
        """准备参考分数和评分标准

        为选定的未批改答案准备参考分数和评分标准。
        使用模型生成评分标准，并对选定的答案进行初步评分。

        Args:
            prepare_system_prompt: 准备阶段的系统提示
            number: 需要处理的答案数量

        Returns:
            生成的评分标准和已处理的学生列表
        """
        response_content = None
        # 确保在评分标准为空或评分数量不符合预期时重试
        count = 0
        while (response_content is None or
               len(response_content['student_scores']) != number or
               response_content['grading_standard'] == ""):
            self.student_score_final = {}
            selected_dict_uncorrected, selected_keys = randomselect_uncorrected(
                self.student_answers_prompt_uncorrected, number
            )
            context_prompt = self.context_prepare_prompt(
                selected_dict_uncorrected, prepare_system_prompt, number
            )
            response = self.ai_client.create_completion(
                model=self.prepare_model,
                messages=context_prompt,
            )
            response_content = self.ai_client.extract_json_from_response(
                response.choices[0].message.content)
            count += 1
            if count % 2 == 0 and number > self.number_prepare_min:
                number -= 1

        logging.info(response_content)
        student_scores = response_content['student_scores']
        grading_standard = response_content['grading_standard']

        for _, (key, value) in enumerate(student_scores.items()):
            self.student_score_final[key] = value

        keys_to_delete = []
        for _, (key, value) in enumerate(selected_dict_uncorrected.items()):
            try:
                value_ = value.copy()
                value_.append(
                    {
                        "role": "assistant",
                        "content": str({key: student_scores[key]}),
                    }
                )
                self.student_answers_prompt_corrected[key] = value_
                # 收集要删除的键
                if key in self.student_answers_prompt_uncorrected:
                    keys_to_delete.append(key)
            except Exception as e:
                logging.error(f"发生错误: {str(e)}")
        
        # 迭代完成后再删除键
        for key in keys_to_delete:
            del self.student_answers_prompt_uncorrected[key]

        logging.info("准备参考分数和评分标准")
        return grading_standard

    def gen_score(self, number_gen: int, selected_dict_uncorrected: Dict[str, List[Dict[str, Any]]],
                  few_shot_learning_system_prompt: List[Dict[str, str]]) -> None:
        """生成学生分数

        使用少样本学习方法为未批改的答案生成分数。
        通过参考已批改的样本，为新的答案生成合适的分数。

        Args:
            number_gen: 用于参考的样本数量
            selected_dict_uncorrected: 选定的未批改答案
            few_shot_learning_system_prompt: 少样本学习系统提示
        """
        student_scores = None

        count = 0
        while student_scores is None:
            # 大模型打分出错了，需要重新生成
            selected_dict_corrected = randompop_corrected(
                self.student_answers_prompt_corrected, number_gen
            )  # 换一波学生样本重新打分
            context_prompt = context_few_shot_learning_prompt(
                selected_dict_uncorrected,
                selected_dict_corrected,
                few_shot_learning_system_prompt,
            )
            response = self.ai_client.create_completion(
                model=self.gen_model,
                messages=context_prompt,
            )
            response_content = self.ai_client.extract_json_from_response(
                response.choices[0].message.content)
            # 有时候提取出来没有student_scores，而是直接返回了分数
            try:
                student_scores = response_content['student_scores']
            except Exception as e:
                student_scores = response_content
            logging.info(student_scores)
            count += 1
            if count % 2 == 0 and number_gen > self.number_gen_min:
                number_gen -= 1  # 可能是参考样本太多了导致提示词过长了

        with self.lock:
            for _, (key, value) in enumerate(student_scores.items()):
                self.student_score_final[key] = value
            
            # 调用回调函数
            if self.score_callback:
                self.score_callback(self.student_score_final.copy(), list(student_scores.keys()))

        for _, (key, value) in enumerate(selected_dict_uncorrected.items()):
            try:
                value_ = value.copy()
                value_.append(
                    {
                        "role": "assistant",
                        "content": str({key: student_scores[key]}),
                    }
                )
                self.student_answers_prompt_corrected[key] = value_
            except Exception as e:
                logging.error(f"发生错误: {str(e)}")
        


    def normalize_score(self, student_scores: Dict[str, float], normalized_min: float = 60,
                        normalized_max: float = 85, original_min: float = 20,
                        original_max: float = 90) -> Dict[str, float]:
        """对学生成绩进行归一化处理

        将原始分数进行归一化处理，对特殊分数区间的成绩进行特殊处理。

        Args:
            student_scores: 包含学生最终成绩的字典
            normalized_min: 归一化后的最小分数
            normalized_max: 归一化后的最大分数
            original_min: 原始成绩的最小值
            original_max: 原始成绩的最大值

        Returns:
            归一化处理后的成绩字典
        """
        def scale_score(score):
            # 对于原始分数特别高或者特别低的，直接返回原始分数，中间那些捞一手（基本上缩放后的分数都比原分数高很多）
            if score < original_min or score > original_max:
                return score
            else:
                # 对其他分数进行缩放
                return score / 100 * (normalized_max - normalized_min) + normalized_min

        return {name: scale_score(score) for name, score in student_scores.items()}

    def get_final_scores(self) -> Dict[str, Any]:
        """获取最终分数

        Returns:
            学生最终分数字典
        """
        return self.student_score_final

    def get_corrected_answers(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取已批改的答案

        Returns:
            已批改的学生答案字典
        """
        return self.student_answers_prompt_corrected
    
    def get_uncorrected_answers(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取已批改的答案

        Returns:
            未批改的学生答案字典
        """
        return self.student_answers_prompt_uncorrected
