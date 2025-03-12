from crawler.interface import HomeworkProcessor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading
import requests
import time
from webdriver_manager.chrome import ChromeDriverManager
import logging
from typing import Dict, List, Any
from queue import Queue
from utils.tools import *


class ChaoxingHomeworkProcessor(HomeworkProcessor):
    """超星学习通作业处理器实现类

    基于HomeworkProcessor接口实现的超星学习通作业处理器，
    负责获取作业列表、处理学生数据和保存结果。
    """

    def __init__(self, driver: webdriver.Chrome, session_cookies: Dict, headers: Dict,
                 driver_queue: Queue, config: Any):
        """初始化作业处理器

        Args:
            driver: Chrome浏览器驱动实例
            session_cookies: 会话Cookie信息
            headers: HTTP请求头信息
            driver_queue: WebDriver实例队列，用于多线程处理
            download_dir: 下载目录路径
            config: 配置信息对象
        """
        self.driver = driver
        self.session_cookies = session_cookies
        self.headers = headers
        self.driver_queue = driver_queue
        self.config = config

    def get_students_grading_url(self, homework_grading_url):
        """获取所有学生批阅链接

        从批阅页面获取学生的答案数据列表。

        Args:
            homework_grading_url: 单个作业批阅页面URL

        Returns:
            所有学生批阅链接数据列表
        """
        student_data = []
        self.driver.get(homework_grading_url)
        time.sleep(2)  # 等待页面加载
        try:
            logs = self.driver.get_log("performance")
            target_url = extract_url_from_logs(
                logs,
                "mooc2-ans/work/mark-list",
                "捕获的目标批阅列表请求 URL: "
            )

            target_url = target_url.replace("pages=1", "pages={}")
            final_page_num = 1

            while True:
                target_url_modified = target_url.format(final_page_num)
                response = requests.get(
                    target_url_modified,
                    headers=self.headers,
                    cookies=self.session_cookies,
                )

                if response.status_code == 200:
                    pass
                else:
                    logging.error(f"请求失败，状态码：{response.status_code}")
                    break

                soup = BeautifulSoup(response.content, "html.parser")

                # 检查是否有 "暂无数据"
                null_data = soup.find("div", class_="nullData")
                if null_data and "暂无数据" in null_data.text:
                    logging.info("已超出页数，停止爬取。")
                    break

                final_page_num += 1
                # 查找每个 ul 元素
                ul_elements = soup.find_all("ul", class_="dataBody_td")

                # 遍历 ul 元素，提取学生名字和批阅链接
                for ul in ul_elements:
                    # 提取学生名字
                    name_div = ul.find("div", class_="py_name")
                    student_name = name_div.text.strip() if name_div else "未找到名字"

                    # 提取批阅链接
                    review_link_tag = ul.find("a", class_="cz_py")
                    review_link = (
                        "https://mooc2-ans.chaoxing.com" +
                        review_link_tag["href"]
                        if review_link_tag
                        else "未找到批阅链接"
                    )

                    # 存储学生数据
                    student_data.append(
                        {"name": student_name, "review_link": review_link})

            return student_data
        except Exception as e:
            logging.error(f'获取学生数据失败：{str(e)}')
            return student_data

    def process_student_data(self, student_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理学生数据

        处理学生的答案数据，包括文本答案和图片答案。

        Args:
            student_data: 学生数据列表

        Returns:
            处理后的学生答案字典
        """
        task_list = {}
        try:
            # 创建多个WebDriver实例
            num_threads = self.config.max_workers_prepare
            if self.driver_queue.empty():
                for _ in range(num_threads):
                    options = webdriver.ChromeOptions()
                    driver_ = webdriver.Chrome(
                        service=Service(ChromeDriverManager().install()),
                        options=options
                    )
                    self.driver_queue.put(driver_)

            # 创建线程锁
            task_list_lock = threading.Lock()

            # 使用线程池处理学生数据
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for student in student_data:
                    future = executor.submit(
                        self._process_student,
                        student,
                        self.headers,
                        self.session_cookies,
                        self.driver_queue,
                        task_list_lock,
                        task_list,
                    )
                    futures.append(future)

                # 等待所有任务完成
                for future in futures:
                    future.result()

            return task_list
        except Exception as e:
            logging.error(f'处理学生答案失败：{str(e)}')
            return task_list

    def _process_student(self, student, headers, session_cookies, driver_queue, task_list_lock, task_list):
        """处理单个学生的作业数据

        获取并处理单个学生的作业答案，包括文本答案和图片答案。

        Args:
            student: 学生信息，包含姓名和作业链接
            headers: HTTP请求头
            session_cookies: 会话Cookie
            driver_queue: WebDriver实例队列
            task_list_lock: 线程锁
            task_list: 存储所有学生答案的字典
        """
        # 从队列中获取driver
        driver = driver_queue.get()
        try:
            student_name = student["name"]
            student_url = student["review_link"]
            driver.get(student_url)
            time.sleep(2)

            logs = driver.get_log("performance")
            target_url = extract_url_from_logs(
                logs,
                "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
            )

            if target_url:
                response = requests.get(
                    target_url, headers=headers, cookies=session_cookies)
                soup = BeautifulSoup(response.content, "html.parser")
                all_questions = []
                question_blocks = soup.find_all("div", class_="mark_item1")

                for block in question_blocks:
                    # 提取题目描述
                    question_description_tag = block.find(
                        "div", class_="hiddenTitle")
                    question_description = question_description_tag.text.strip()

                    # 提取学生答案
                    student_answer_tag = block.find(
                        "dl",
                        class_="mark_fill",
                        id=lambda x: x and x.startswith("stuanswer_"),
                    )
                    if student_answer_tag:
                        # 查找文字答案
                        text_answers = [
                            p.text.strip()
                            for p in student_answer_tag.find_all("p")
                            if p.text.strip()
                        ]
                        # 查找图片链接
                        image_answers = [
                            img["src"]
                            for img in student_answer_tag.find_all("img")
                            if "src" in img.attrs
                        ]
                        # 组合学生答案
                        student_answer = {"text": text_answers,
                                          "images": image_answers}
                    else:
                        # 空着呢
                        student_answer = {"text": [], "images": []}

                    # 提取参考答案
                    correct_answer_tag = block.find(
                        "dl",
                        class_="mark_fill",
                        id=lambda x: x and x.startswith("correctanswer_"),
                    )
                    if correct_answer_tag:
                        correct_answer = correct_answer_tag.text.strip()
                    else:
                        correct_answer = "此题无参考答案"

                    # 存储题目信息
                    question_data = {
                        "description": question_description,
                        "student_answer": student_answer,
                        "correct_answer": correct_answer.replace("参考答案：", "", 1),
                    }
                    all_questions.append(question_data)

                # 使用锁来保护共享资源
                with task_list_lock:
                    task_list[student_name] = all_questions
        finally:
            # 将driver放回队列
            driver_queue.put(driver)

    def process_results(self, results) -> None:
        """保存处理结果

        将处理后的学生答案保存到JSON文件。

        Args:
            results: 处理后的学生答案字典
        """
        final_results = {
            "题目": {},
            "学生回答": {}
        }

        student_name_list = list(results.keys())
        if not student_name_list:
            logging.warning("没有学生数据可保存")
            return final_results

        len_task = len(results[student_name_list[0]])

        # 初始化学生回答字典
        for student_name in student_name_list:
            final_results["学生回答"][student_name] = {}

        # 处理每道题目
        for i in range(len_task):
            question_key = "题目" + str(i + 1)
            final_results["题目"][question_key] = {
                "题干": results[student_name_list[0]][i]["description"],
                "正确答案": results[student_name_list[0]][i]["correct_answer"]
            }
            for student_name in student_name_list:
                final_results["学生回答"][student_name][question_key] = \
                    results[student_name][i]["student_answer"]
        
        # 转换为数据库需要的格式：学生答案列表
        db_results = []
        for student_name, answers in final_results["学生回答"].items():
            student_data = {
                "姓名": student_name,
                "学号": "",  # 如果有学号数据，可以在此处添加
                "答案": answers
            }
            db_results.append(student_data)
        
        return {
            "json_result": final_results,
            "db_result": db_results
        }
