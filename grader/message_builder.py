import re
import json
import logging
from typing import Dict, List, Any
from .interface import IMessageBuilder
from utils import download_image
from concurrent.futures import ThreadPoolExecutor, as_completed


class MessageBuilder(IMessageBuilder):
    """消息构建器类，负责构建发送给OpenAI的消息格式

    该类实现了IMessageBuilder接口，提供了创建包含图片的消息列表、
    生成系统提示信息和少样本学习系统提示的功能。

    Attributes:
        prepare_system_prompt (str): 准备阶段的系统提示模板
        few_shot_learning_system_prompt (str): 少样本学习系统提示模板
    """

    def __init__(self, prepare_system_prompt: str, few_shot_learning_system_prompt: str):
        """初始化消息构建器

        Args:
            prepare_system_prompt: 准备阶段的系统提示模板
            few_shot_learning_system_prompt: 少样本学习系统提示模板
        """
        self.prepare_system_prompt = prepare_system_prompt
        self.few_shot_learning_system_prompt = few_shot_learning_system_prompt

    @staticmethod
    def create_student_messages_with_images(homework_data: Dict[str, Any], student_name: str) -> List[Dict[str, Any]]:
        """创建包含图片的消息列表

        为指定学生创建包含文本答案和图片的消息列表，用于后续的评分。
        将学生的文本答案和图片整合成标准的消息格式。

        Args:
            homework_data: 作业数据，包含学生答案和题目信息
            student_name: 学生姓名，用于标识具体学生的答案

        Returns:
            包含学生答案和图片的消息列表，每个元素都是标准的消息格式字典
        """

        user_prompt = student_name + "：\n"
        student_answers = homework_data["学生回答"][student_name]
        image_counter = 0
        # 收集所有需要下载的图片URL
        image_urls_map = {}

        # 遍历学生的所有回答
        for _, (question, answer) in enumerate(student_answers.items(), 1):
            # 添加问题和文本答案
            answer_text = answer["text"][0] if answer["text"] else ""
            user_prompt += question + "：" + answer_text + "\n"

            # 处理学生提交的截图
            user_prompt += "本题学生截图："
            if not answer["images"]:
                user_prompt += "" + "\n" + "---" + "\n"
                continue

            # 添加图片引用
            for image_url in answer["images"]:
                image_counter += 1
                image_id = str(image_counter)
                user_prompt += f"<img{image_id}>,"
                image_urls_map["img"+str(image_id)] = image_url

            user_prompt += "\n" + "---" + "\n"

        # 下载所有图片并创建消息列表
        image_content_list = MessageBuilder.download_images(image_urls_map)
        text_content_list = [{"type": "text", "text": user_prompt}]
        content_list = text_content_list + image_content_list
        # 添加文本消息
        student_answers_list = [{"role": "user", "content": content_list}]
        return student_answers_list

    @staticmethod
    def download_images(image_urls_map: Dict[str, str]) -> List[Dict[str, Any]]:
        """下载学生提交的所有图片

        Args:
            image_urls_map: 包含图片标识和图片URL的字典

        Returns:
            包含已下载图片的消息列表
        """
        image_content_list = []

        # 并行下载所有图片
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_img = {
                executor.submit(download_image, url): (img_tag, url)
                for img_tag, url in image_urls_map.items()
            }

            for future in as_completed(future_to_img):
                img_tag, url = future_to_img[future]
                try:
                    img_base64 = future.result()
                    if img_base64:
                        image_content_list.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                },
                                "detail": img_tag
                            }
                        )
                    else:
                        logging.warning(f"无法下载图片: {url}")
                except Exception as exc:
                    logging.error(f"下载图片时出错: {url}: {exc}")

        return image_content_list

    def _build_question_stem(self, homework_data: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """构建题目内容字符串

        将作业数据中的题目信息和正确答案格式化为系统提示使用的字符串。

        Args:
            homework_data: 作业数据，包含题目信息和答案

        Returns:
            格式化后的题目内容字符串和相关图片内容列表的元组
        """
        image_counter = 0
        image_urls_map = {}
        question_stem = "###\n"
        for _, (key, value) in enumerate(homework_data["题目"].items(), start=1):
            question_stem += f"{key}：{value['题干']['text']}\n正确答案：{value['正确答案']}\n截图参考："
            for image_url in value['题干']['images']:
                image_counter += 1
                image_id = str(image_counter)
                question_stem += f"<img{image_id}>,"
                image_urls_map["img"+str(image_id)] = image_url

            question_stem += "\n###"

        image_content_list = MessageBuilder.download_images(image_urls_map)
        return question_stem, image_content_list

    def gen_prepare_system_prompt(self, homework_data: Dict[str, Any], number: int) -> List[Dict[str, Any]]:
        """生成系统提示信息

        生成包含题目和评分规则的系统提示信息，用于指导模型进行评分。
        将题目信息和评分规则整合成标准的提示格式。

        Args:
            homework_data: 作业数据，包含题目信息和答案
            number: 需要处理的题目数量

        Returns:
            包含系统提示信息的消息列表，用于模型评分
        """
        question_stem, image_content_list = self._build_question_stem(
            homework_data)

        system_prompt = self.prepare_system_prompt.format(
            question_stem=question_stem,
            number=str(number),
            number_=str(number-1)
        )
        text_content_list = [{"type": "text", "text": system_prompt}]
        content_list = text_content_list + image_content_list
        messages = [{"role": "system", "content": content_list}]
        return messages

    def gen_few_shot_learning_system_prompt(self, homework_data: Dict[str, Any], grading_standard: str) -> List[Dict[str, Any]]:
        """生成少样本学习系统提示

        生成用于少样本学习的系统提示信息，包含题目信息和评分标准。
        整合题目信息和评分标准，生成引导模型进行少样本学习的提示。

        Args:
            homework_data: 作业数据，包含题目信息和答案
            grading_standard: 评分标准，用于指导模型评分

        Returns:
            包含系统提示信息的消息列表，用于模型进行少样本学习
        """
        question_stem, image_content_list = self._build_question_stem(
            homework_data)

        system_prompt = self.few_shot_learning_system_prompt.format(
            question_stem=question_stem,
            grading_standard=grading_standard
        )
        text_content_list = [{"type": "text", "text": system_prompt}]
        content_list = text_content_list + image_content_list
        messages = [{"role": "system", "content": content_list}]
        return messages
