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
from typing import Dict, List, Any, Optional, Tuple
from queue import Queue
from utils.tools import *


class ChaoxingHomeworkProcessor(HomeworkProcessor):
    """超星学习通作业处理器实现类

    基于HomeworkProcessor接口实现的超星学习通作业处理器，
    负责获取学生作业数据、处理答案内容和格式化最终结果。
    支持多线程并行处理以提高效率。
    """

    def __init__(self, driver: webdriver.Chrome, session_cookies: Dict, headers: Dict,
                 driver_queue: Queue, config: Any):
        """初始化作业处理器

        Args:
            driver: Chrome浏览器驱动实例
            session_cookies: 会话Cookie信息
            headers: HTTP请求头信息
            driver_queue: WebDriver实例队列，用于多线程处理
            config: 配置信息对象
        """
        self.driver = driver
        self.session_cookies = session_cookies
        self.headers = headers
        self.driver_queue = driver_queue
        self.config = config
        self.task_list_lock = threading.Lock()  # 添加线程锁作为实例变量

    def get_students_grading_url(self, homework_grading_url: str) -> List[Dict[str, Any]]:
        """获取所有学生的作业批阅链接

        从批阅页面获取学生的作业提交列表及批阅链接。

        Args:
            homework_grading_url: 作业批阅页面URL

        Returns:
            List[Dict[str, Any]]: 学生作业批阅信息列表，包含姓名和批阅链接
        """
        student_data = []
        logging.info(f"正在获取学生作业批阅链接列表: {homework_grading_url}")

        try:
            # 访问作业批阅页面
            self.driver.get(homework_grading_url)
            time.sleep(2)  # 等待页面加载

            # 从性能日志中提取批阅列表请求URL
            logs = self.driver.get_log("performance")
            mark_list_url = extract_url_from_logs(
                logs,
                "mooc2-ans/work/mark-list",
                "捕获的学生批阅列表请求 URL: "
            )

            if not mark_list_url:
                logging.error("未能捕获到学生批阅列表URL")
                return student_data

            # 修改URL以支持分页查询
            paginated_url = mark_list_url.replace("pages=1", "pages={}")
            current_page = 1

            # 遍历所有页面获取学生数据
            while True:
                page_url = paginated_url.format(current_page)
                logging.info(f"正在获取第 {current_page} 页学生数据")

                # 请求当前页数据
                response = requests.get(
                    page_url,
                    headers=self.headers,
                    cookies=self.session_cookies,
                )

                if response.status_code != 200:
                    logging.error(
                        f"请求第 {current_page} 页失败，状态码：{response.status_code}")
                    break

                # 解析页面内容
                soup = BeautifulSoup(response.content, "html.parser")

                # 检查是否有 "暂无数据"
                null_data = soup.find("div", class_="nullData")
                if null_data and "暂无数据" in null_data.text:
                    logging.info(f"第 {current_page} 页暂无数据，爬取完成")
                    break

                # 查找学生数据
                ul_elements = soup.find_all("ul", class_="dataBody_td")
                if not ul_elements:
                    logging.info(f"第 {current_page} 页未找到学生数据，停止爬取")
                    break

                # 提取学生信息
                for ul in ul_elements:
                    student_info = self._extract_student_info(ul)
                    if student_info:
                        student_data.append(student_info)

                current_page += 1

            logging.info(f"共获取到 {len(student_data)} 名学生的作业批阅链接")
            return student_data

        except Exception as e:
            logging.error(f'获取学生批阅链接失败：{str(e)}')
            return student_data

    def _extract_student_info(self, ul_element) -> Optional[Dict[str, str]]:
        """从HTML元素中提取学生信息

        Args:
            ul_element: 包含学生信息的HTML元素

        Returns:
            Optional[Dict[str, str]]: 学生信息字典，包含姓名和批阅链接
        """
        try:
            # 提取学生名字
            name_div = ul_element.find("div", class_="py_name")
            student_name = name_div.text.strip() if name_div else None

            if not student_name:
                return None

            # 提取批阅链接
            review_link_tag = ul_element.find("a", class_="cz_py")
            if not review_link_tag or "href" not in review_link_tag.attrs:
                return None

            review_link = "https://mooc2-ans.chaoxing.com" + \
                review_link_tag["data"].replace("&amp;", "&")

            return {"name": student_name, "review_link": review_link}
        except Exception as e:
            logging.error(f"提取学生信息失败: {str(e)}")
            return None

    def process_student_data(self, student_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理学生作业数据

        使用多线程并行处理多名学生的作业答案。

        Args:
            student_data: 学生数据列表，包含姓名和批阅链接

        Returns:
            Dict[str, Any]: 处理后的学生答案字典，以学生姓名为键
        """
        task_list = {}

        if not student_data:
            logging.warning("没有学生数据需要处理")
            return task_list

        logging.info(f"开始处理 {len(student_data)} 名学生的作业数据")

        try:
            # 准备WebDriver队列
            self._prepare_driver_queue()

            # 使用线程池处理学生数据
            num_threads = min(
                self.config.max_workers_prepare, len(student_data))
            logging.info(f"使用 {num_threads} 个线程并行处理")

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for student in student_data:
                    future = executor.submit(
                        self._process_single_student,
                        student,
                        self.headers,
                        self.session_cookies,
                        self.driver_queue,
                        task_list,
                    )
                    futures.append(future)

                # 等待所有任务完成
                for future in futures:
                    future.result()

            logging.info(f"成功处理 {len(task_list)} 名学生的作业数据")
            return task_list
        except Exception as e:
            logging.error(f'处理学生答案失败：{str(e)}')
            return task_list

    def _prepare_driver_queue(self) -> None:
        """准备WebDriver队列

        确保队列中有足够的WebDriver实例用于多线程处理。
        """
        if self.driver_queue.empty():
            num_threads = self.config.max_workers_prepare
            logging.info(f"正在创建 {num_threads} 个WebDriver实例")

            for _ in range(num_threads):
                options = webdriver.ChromeOptions()
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )
                self.driver_queue.put(driver)

    def _process_single_student(self, student: Dict[str, str], headers: Dict,
                                session_cookies: Dict, driver_queue: Queue,
                                task_list: Dict[str, List[Dict[str, Any]]]) -> None:
        """处理单个学生的作业数据

        获取并解析单个学生的作业答案内容。

        Args:
            student: 学生信息，包含姓名和作业链接
            headers: HTTP请求头
            session_cookies: 会话Cookie
            driver_queue: WebDriver实例队列
            task_list: 存储所有学生答案的字典
        """
        # 从队列中获取driver
        driver = driver_queue.get()
        student_name = student["name"]

        try:
            logging.info(f"开始处理学生 '{student_name}' 的作业")
            student_url = student["review_link"]
            # 访问学生作业页面
            driver.get(student_url)
            time.sleep(2)

            # 获取作业内容请求URL
            logs = driver.get_log("performance")
            review_content_url = extract_url_from_logs(
                logs,
                "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
            )

            if not review_content_url:
                logging.warning(f"未能获取学生 '{student_name}' 的作业内容URL")
                return

            # 请求作业内容
            response = requests.get(
                review_content_url,
                headers=headers,
                cookies=session_cookies
            )

            if response.status_code != 200:
                logging.error(
                    f"获取学生 '{student_name}' 作业内容失败，状态码: {response.status_code}")
                return

            # 解析作业内容
            soup = BeautifulSoup(response.content, "html.parser")
            question_blocks = soup.find_all("div", class_="mark_item1")

            if not question_blocks:
                logging.warning(f"未找到学生 '{student_name}' 的作业题目内容")
                return

            all_questions = []
            for block in question_blocks:
                question_data = self._extract_question_data(block)
                all_questions.append(question_data)

            # 保存学生作业数据
            with self.task_list_lock:
                task_list[student_name] = all_questions

            logging.info(
                f"成功处理学生 '{student_name}' 的作业，包含 {len(all_questions)} 道题目")

        except Exception as e:
            logging.error(f"处理学生 '{student_name}' 作业失败: {str(e)}")
        finally:
            # 将driver放回队列
            driver_queue.put(driver)

    def _extract_question_data(self, question_block) -> Dict[str, Any]:
        """从HTML元素中提取题目数据

        Args:
            question_block: 包含题目信息的HTML元素

        Returns:
            Dict[str, Any]: 题目数据字典
        """
        # 提取题目描述
        question_description = self._extract_content(
            question_block.find("div", class_="hiddenTitle")
        )

        # 提取学生答案
        student_answer_tag = question_block.find(
            "dl",
            class_="mark_fill",
            id=lambda x: x and x.startswith("stuanswer_"),
        )
        student_answer = self._extract_content(
            student_answer_tag) if student_answer_tag else {"text": [], "images": []}

        # 提取参考答案
        correct_answer_tag = question_block.find(
            "dl",
            class_="mark_fill",
            id=lambda x: x and x.startswith("correctanswer_"),
        )
        correct_answer = correct_answer_tag.text.strip().replace(
            "参考答案：", "", 1) if correct_answer_tag else "此题无参考答案"

        return {
            "description": question_description,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
        }

    def _extract_content(self, element) -> Dict[str, List[str]]:
        """提取HTML元素中的文本和图片内容"""
        if not element:
            return {"text": [], "images": []}

        # 提取文字部分，处理<br>标签
        text_contents = []
        for p in element.find_all("p"):
            if not p:
                continue

            # 获取<p>的原始HTML内容
            html_content = str(p)
            # 将<br>替换为特定标记
            html_content = html_content.replace(
                '<br>', '\n').replace('<br/>', '\n')
            # 创建新的BeautifulSoup对象解析处理后的HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            # 获取文本内容
            p_content = soup.get_text().strip()

            if p_content:
                text_contents.append(p_content)

        # 提取图片链接
        image_urls = [
            img["src"]
            for img in element.find_all("img")
            if "src" in img.attrs
        ]
        
        # 将多个段落文本用换行符连接成一个字符串
        combined_text = []
        if text_contents:
            combined_text = ["\n".join(text_contents)]

        return {"text": combined_text, "images": image_urls}

    def process_results(self, results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """处理最终结果

        格式化学生答案数据为更易用的结构。

        Args:
            results: 学生答案原始数据

        Returns:
            Dict[str, Any]: 格式化后的最终结果
        """
        final_results = {
            "题目": {},
            "学生回答": {}
        }

        student_name_list = list(results.keys())
        if not student_name_list:
            logging.warning("没有学生数据可处理")
            return final_results

        logging.info(f"正在格式化 {len(student_name_list)} 名学生的作业数据")

        # 获取题目数量
        first_student = student_name_list[0]
        question_count = len(results[first_student])

        # 初始化学生回答字典
        for student_name in student_name_list:
            final_results["学生回答"][student_name] = {}

        # 处理每道题目
        for i in range(question_count):
            question_key = f"题目{i + 1}"

            # 添加题目信息和参考答案
            final_results["题目"][question_key] = {
                "题干": results[first_student][i]["description"],
                "正确答案": results[first_student][i]["correct_answer"]
            }

            # 添加每位学生的答案
            for student_name in student_name_list:
                if i < len(results[student_name]):  # 确保索引有效
                    final_results["学生回答"][student_name][question_key] = \
                        results[student_name][i]["student_answer"]

        logging.info(f"成功格式化 {question_count} 道题目的作业数据")
        return final_results
