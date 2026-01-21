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
        student_answers = homework_data["学生回答"][student_name]

        # 构建交错排列的content数组
        content_parts = [
            {
                "type": "text",
                "text": f"{student_name}的作业答案：\n请根据下面提供的题目和对应图片进行评分。"
            }
        ]

        # 收集所有图片URL用于下载
        all_image_urls = []
        image_counter = 0

        # 遍历学生的所有回答
        for question_num, (question, answer) in enumerate(student_answers.items(), 1):
            # 添加问题和文本答案
            answer_text = answer["text"][0] if answer["text"] else ""
            content_parts.append({
                "type": "text",
                "text": f"\n题目{question_num}：\n学生答案：{answer_text}"
            })

            # 处理学生提交的截图
            if answer["images"]:
                content_parts.append({
                    "type": "text",
                    "text": f"题目{question_num}对应的学生截图："
                })

                # 为每张图片添加标识和图片内容
                for image_url in answer["images"]:
                    image_counter += 1
                    all_image_urls.append(image_url)

                    # 预留图片位置（稍后会被实际图片替换）
                    content_parts.append({
                        "type": "image_placeholder",
                        "image_url": image_url,
                        "image_id": image_counter
                    })
            else:
                content_parts.append({
                    "type": "text",
                    "text": f"题目{question_num}：学生未提交截图"
                })

            # content_parts.append({
            #     "type": "text",
            #     "text": "---"
            # })

        # 下载所有图片
        downloaded_images = MessageBuilder.download_images(all_image_urls)

        # 创建图片URL到base64的映射
        image_map = {}
        for i, image_url in enumerate(all_image_urls):
            if i < len(downloaded_images):
                image_map[image_url] = downloaded_images[i]

        # 替换占位符为实际图片
        final_content_parts = []
        for part in content_parts:
            if part["type"] == "image_placeholder":
                if part["image_url"] in image_map:
                    final_content_parts.append(image_map[part["image_url"]])
                else:
                    # 如果图片下载失败，添加错误提示
                    final_content_parts.append({
                        "type": "text",
                        "text": f"[图{part['image_id']}下载失败]"
                    })
            else:
                final_content_parts.append(part)

        # 创建最终的消息列表
        student_answers_list = [
            {"role": "user", "content": final_content_parts}]
        return student_answers_list

    @staticmethod
    def download_images(image_urls: List[str]) -> List[Dict[str, Any]]:
        """下载学生提交的所有图片

        Args:
            image_urls: 图片URL的列表

        Returns:
            包含已下载图片的消息列表
        """
        image_content_list = []

        # 并行下载所有图片
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_img = {
                executor.submit(download_image, url): url
                for url in image_urls  # 修复：移除.items()
            }

            for future in as_completed(future_to_img):
                url = future_to_img[future]  # 修复：移除不必要的解包
                try:
                    img_base64 = future.result()
                    if img_base64:
                        image_content_list.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                },
                            }
                        )
                    else:
                        logging.warning(f"无法下载图片: {url}")
                except Exception as exc:
                    logging.error(f"下载图片时出错: {url}: {exc}")

        return image_content_list

    def _build_question_stem(self, homework_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """构建题目内容字符串

        将作业数据中的题目信息和正确答案格式化为系统提示使用的内容列表。
        采用与create_student_messages_with_images相同的组织方式。

        Args:
            homework_data: 作业数据，包含题目信息和答案

        Returns:
            格式化后的题目内容列表和相关图片内容列表的元组
        """
        # 构建交错排列的content数组
        content_parts = [
            {
                "type": "text",
                "text": "题目信息和参考答案：\n请根据以下题目和参考截图进行评分。"
            }
        ]

        # 收集所有图片URL用于下载
        all_image_urls = []
        image_counter = 0

        # 遍历所有题目
        for question_num, (key, value) in enumerate(homework_data["题目"].items(), start=1):
            # 添加题目和正确答案
            content_parts.append({
                "type": "text",
                "text": f"\n题目{question_num}：{key}\n题干：{value['题干']['text']}\n正确答案：{value['正确答案']}"
            })

            # 处理题目的参考截图
            if value['题干']['images']:
                content_parts.append({
                    "type": "text",
                    "text": f"题目{question_num}对应的参考截图："
                })

                # 为每张图片添加标识和图片内容
                for image_url in value['题干']['images']:
                    image_counter += 1
                    all_image_urls.append(image_url)

                    # 预留图片位置（稍后会被实际图片替换）
                    content_parts.append({
                        "type": "image_placeholder",
                        "image_url": image_url,
                        "image_id": image_counter
                    })
            else:
                content_parts.append({
                    "type": "text",
                    "text": f"题目{question_num}：无参考截图"
                })

            content_parts.append({
                "type": "text",
                "text": "---"
            })

        # 下载所有图片
        downloaded_images = MessageBuilder.download_images(all_image_urls)

        # 创建图片URL到base64的映射
        image_map = {}
        for i, image_url in enumerate(all_image_urls):
            if i < len(downloaded_images):
                image_map[image_url] = downloaded_images[i]

        # 替换占位符为实际图片
        final_content_parts = []
        for part in content_parts:
            if part["type"] == "image_placeholder":
                if part["image_url"] in image_map:
                    final_content_parts.append(image_map[part["image_url"]])
                else:
                    # 如果图片下载失败，添加错误提示
                    final_content_parts.append({
                        "type": "text",
                        "text": f"[参考图{part['image_id']}下载失败]"
                    })
            else:
                final_content_parts.append(part)

        return final_content_parts

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
        final_content_parts = self._build_question_stem(
            homework_data)

        system_prompt = self.prepare_system_prompt.format(
            number=str(number),
            number_=str(number-1)
        )
        text_content_list = [{"type": "text", "text": system_prompt}]
        messages = [{"role": "system", "content": text_content_list},
                    {"role": "user", "content": final_content_parts},
                    {"role": "assistant", "content": '好，我已经了解题目及其参考答案和参考截图，接下来请提供学生的作答。'}]
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
        final_content_parts = self._build_question_stem(
            homework_data)

        system_prompt = self.few_shot_learning_system_prompt.format(
            grading_standard=grading_standard
        )
        text_content_list = [{"type": "text", "text": system_prompt}]
        messages = [{"role": "system", "content": text_content_list},
                    {"role": "user", "content": final_content_parts},
                    {"role": "assistant", "content": '好，我已经了解题目及其参考答案和参考截图，接下来请提供学生的作答。'}]
        return messages
