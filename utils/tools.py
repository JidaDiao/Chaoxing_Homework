import json
import base64
import requests
from io import BytesIO
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image
import time
import os
import shutil
import xlrd
from xlutils.copy import copy
import glob
import re
import logging


def import_json_file(file_path):
    """
    导入JSON文件并返回其内容。

    :param file_path: JSON文件的路径
    :return: 解析后的JSON内容
    """
    try:
        logging.info(f'导入JSON文件: {file_path}')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        logging.error(f"文件未找到: {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"JSON文件解析错误: {file_path}")
        return None


def download_image(url_or_base64):
    """
    下载图片或处理Base64格式图片，并压缩以减少字符串长度。

    :param url_or_base64: 图片的URL或Base64字符串
    :return: 压缩后的Base64字符串
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Referer': url_or_base64  # 添加来源页面，部分网站需要
    }
    try:
        logging.info(f'处理图片: {url_or_base64}')
        if url_or_base64.startswith("data:image/"):  # 判断是否是 Base64 图片
            # 处理 Base64 数据
            base64_data = url_or_base64.split(",")[1]
            image_bytes = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_bytes))
        else:
            # 下载图片
            response = requests.get(url_or_base64, headers=headers, timeout=10)
            if response.status_code == 200:
                image_bytes = BytesIO(response.content).read()
                image = Image.open(BytesIO(image_bytes))
            else:
                logging.error(f"请求失败，状态码: {response.status_code}")
                return None

        # 确保图片模式为 RGB（JPEG 不支持 RGBA 模式）
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # 将图像分辨率调整为原来的80%
        width, height = image.size
        new_size = (int(width * 0.8), int(height * 0.8))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        # 压缩图片并转换为 Base64 格式
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        compressed_image_bytes = buffered.getvalue()

        return base64.b64encode(compressed_image_bytes).decode('utf-8')

    except Exception as e:
        logging.error(f'发生错误: {str(e)}')
        return None


def randomselect_uncorrected(uncorrected_answers, num_to_select):
    """
    随机选择未批改的学生答案。

    :param uncorrected_answers: 未批改的学生答案字典
    :param num_to_select: 需要选择的答案数量
    :return: 选择的答案字典和对应的键列表
    """
    selected_keys = random.sample(
        list(uncorrected_answers.keys()), num_to_select)
    selected_dict = {key: uncorrected_answers[key] for key in selected_keys}
    logging.info(f'随机选择了 {num_to_select} 个学生答案')
    return selected_dict, selected_keys


def pop_uncorrected(uncorrected_answers, keys_to_remove):
    """
    从未批改的学生答案中删除已选择的键。

    :param uncorrected_answers: 未批改的学生答案字典
    :param keys_to_remove: 已选择的键列表
    """
    for key in keys_to_remove:
        uncorrected_answers.pop(key, None)
    logging.info('从未批改的学生答案中删除已选择的键')


def randompop_corrected(corrected_answers, num_to_select):
    """
    随机选择已批改的学生答案。

    :param corrected_answers: 已批改的学生答案字典
    :param num_to_select: 需要选择的答案数量
    :return: 选择的答案字典
    """
    selected_keys = random.sample(
        list(corrected_answers.keys()), num_to_select)
    selected_dict = {key: corrected_answers[key] for key in selected_keys}
    return selected_dict


def context_prepare_prompt(selected_answers, system_prompt, num_answers):
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


def context_few_shot_learning_prompt(uncorrected_answers, corrected_answers, system_prompt):
    """
    准备少样本学习的上下文提示信息。

    :param uncorrected_answers: 未批改的学生答案字典
    :param corrected_answers: 已批改的学生答案字典
    :param system_prompt: 少样本学习系统提示信息
    :return: 准备好的上下文提示信息
    """
    context_prompt = system_prompt
    for _, value in corrected_answers.items():
        context_prompt += value
    for _, value in uncorrected_answers.items():
        context_prompt += value
    return context_prompt


def convert_url(original_url, page_number=1):
    """
    将链接1的URL转换为链接2的格式，并支持指定翻页。

    :param original_url: 原始链接
    :param page_number: 页码，默认为1
    :return: 转换后的链接
    """
    parsed_url = urlparse(original_url)
    query_params = parse_qs(parsed_url.query)

    courseid = query_params.get("courseid", [""])[0]
    clazzid = query_params.get("clazzid", [""])[0]
    cpi = query_params.get("cpi", [""])[0]

    new_params = {
        "courseid": courseid,
        "clazzid": clazzid,
        "cpi": cpi,
        "recycle": "0",
        "pid": "0",
        "status": "-1",
        "pages": str(page_number),
        "size": "12",
        "selectClassid": "0",
        "search": "",
        "v": "0",
        "topicid": "0",
    }

    new_query = urlencode(new_params)
    new_url = urlunparse(
        (parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", new_query, ""))
    return new_url


def sanitize_folder_name(folder_name):
    """
    将字符串转换为合法的Windows文件夹名称，尽量少修改。

    :param folder_name: 原始文件夹名称
    :return: 合法的Windows文件夹名称
    """
    invalid_chars = r'[<>:"/\\|?*]'
    reserved_names = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]

    sanitized_name = re.sub(invalid_chars, "_", folder_name)
    sanitized_name = sanitized_name.rstrip(" .")

    if sanitized_name.upper() in reserved_names:
        sanitized_name += "_folder"

    if not sanitized_name:
        sanitized_name = "default_folder"

    return sanitized_name


def download(driver, download_dir, destination_path, page_url):
    """
    使用Selenium下载文件并移动到指定目录。

    :param driver: Selenium WebDriver实例
    :param destination_path: 文件保存路径
    :param page_url: 下载页面的URL
    """
    driver.get(page_url)
    wait = WebDriverWait(driver, 10)

    more_button = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, 'piyue_more')))
    ActionChains(driver).move_to_element(more_button).perform()

    import_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, '//a[@onclick="showImportDiv();"]')))
    import_button.click()

    download_button = driver.find_element(
        By.XPATH, '//a[@onclick="exportScoreTemplate(true)"]')
    download_button.click()

    time.sleep(3)
    move_xls_files(download_dir, destination_path)


def move_xls_files(source_directory, target_directory):
    """
    移动下载的.xls文件到指定目录。

    :param source_directory: 源目录路径
    :param target_directory: 目标目录路径
    """
    if not os.path.exists(source_directory):
        logging.error(f"源目录不存在: {source_directory}")
        return

    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
        logging.info(f"目标目录不存在，已创建: {target_directory}")

    for file_name in os.listdir(source_directory):
        file_path = os.path.join(source_directory, file_name)

        if os.path.isfile(file_path) and file_name.endswith('.xls'):
            shutil.move(file_path, os.path.join(target_directory, file_name))
            logging.info(f"已移动文件: {file_name}")
