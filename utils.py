import json
import base64
import requests
from io import BytesIO
import random
import re


def import_json_file(file_path):
    """
    导入JSON文件并返回其内容。
    
    :param file_path: JSON文件的路径
    :return: 解析后的JSON内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"JSON文件解析错误: {file_path}")
        return None


def download_image(url):
    """下载图片并转换为base64格式"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Referer': url  # 添加来源页面，部分网站需要
    }
    try:
        # 添加 headers 模拟浏览器请求
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # 使用 BytesIO 处理二进制数据
            image_bytes = BytesIO(response.content).read()
            # 转换为 base64 格式
            return base64.b64encode(image_bytes).decode('utf-8')
        else:
            print(f"请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"下载图片失败: {url}, 错误: {str(e)}")
    return None


def randompop_uncorrected(student_answers_prompt_uncorrected, number):
    # 随机选择 n 个键
    selected_keys = random.sample(list(student_answers_prompt_uncorrected.keys()), number)
    # 创建新字典并从原字典删除这些键
    selected_dict = {key: student_answers_prompt_uncorrected.pop(key) for key in selected_keys}
    return selected_dict


def randompop_corrected(student_answers_prompt_corrected, number):
    # 随机选择 n 个键
    selected_keys = random.sample(list(student_answers_prompt_corrected.keys()), number)
    # 创建新字典
    selected_dict = {key: student_answers_prompt_corrected[key] for key in selected_keys}
    return selected_dict


def context_prepare_prompt(selected_dict, prepare_system_prompt, number):
    context_prompt = prepare_system_prompt
    for index, (key, value) in enumerate(selected_dict.items(), start=1):
        context_prompt += value
        if index < number:
            context_prompt.append({
                "role": "assistant",
                "content": "第" + str(index) + "轮：pass"
            })
    return context_prompt


def context_few_shot_learning_prompt(selected_dict_uncorrected, selected_dict_corrected,
                                     few_shot_learning_system_prompt):
    context_prompt = few_shot_learning_system_prompt
    for index, (key, value) in enumerate(selected_dict_corrected.items(), start=1):
        context_prompt += value
    for index, (key, value) in enumerate(selected_dict_uncorrected.items(), start=1):
        context_prompt += value
    return context_prompt


def parse_grading_response(response):
    # 提取学生名字和成绩部分
    # 提取学生名字和成绩
    student_scores = re.findall(r"(\S+)：(\d+)分", response)
    student_dict = {name: int(score) for name, score in student_scores}

    # 提取评分标准
    scoring_standard_match = re.search(r"### 本作业评分标准：\s*(.*)", response, re.DOTALL)
    scoring_standard = scoring_standard_match.group(1).strip() if scoring_standard_match else ""

    return student_dict, scoring_standard
