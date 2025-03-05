from crawler.interface import HomeworkProcessor, LoginStrategy, HomeworkCrawler
from crawler.webdriver_factory import WebDriverFactory
from bs4 import BeautifulSoup
import requests
import time
import os
import json
import logging
from typing import Dict, List, Any
from queue import Queue
from utils.tools import *
from crawler.homework_processor_impl import ChaoxingHomeworkProcessor


class ChaoxingHomeworkCrawler(HomeworkCrawler):
    """超星学习通作业爬虫类

    该类整合了作业爬取的所有功能，包括登录、获取课程链接、解析作业列表、下载作业数据等。
    使用Selenium进行页面操作，支持多线程并行处理以提高效率。

    Attributes:
        driver (webdriver.Chrome): Chrome浏览器驱动实例
        driver_queue (Queue): WebDriver实例队列，用于多线程处理
        session_cookies (dict): 会话Cookie信息
        headers (dict): HTTP请求头信息
        download_dir (str): 下载目录路径
        config (Any): 配置信息对象
    """

    def __init__(self, driver_factory: WebDriverFactory, login_strategy: LoginStrategy, config: Any):
        """初始化作业爬虫

        初始化ChaoxingHomeworkCrawler类的实例，设置必要的属性和WebDriver配置。

        Args:
            driver_factory: WebDriver工厂实例，用于创建WebDriver
            login_strategy: 登录策略实例，用于处理登录逻辑
            config: 配置信息对象
        """
        self.driver = None
        self.driver_queue = Queue()
        self.session_cookies = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"}
        self.config = config
        self.driver_factory = driver_factory
        self.login_strategy = login_strategy
        
        # 初始化下载目录
        download_dir = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        self.download_dir = download_dir
        
        # 初始化处理器
        self.processor = ChaoxingHomeworkProcessor(
            driver=self.driver,
            session_cookies=self.session_cookies,
            headers=self.headers,
            driver_queue=self.driver_queue,
            download_dir=self.download_dir,
            config=self.config
        )

        # 初始化WebDriver
        self.driver = self.driver_factory.create_driver(
            self.config.chrome_driver_path)

    def run(self):
        """运行作业爬虫

        执行完整的作业爬取流程，包括登录、获取作业列表和处理作业数据。

        Returns:
            None
        """
        # 登录
        if not self.login():
            return
        else:
            # 处理每个课程URL
            for course_url in self.config.course_urls:
                # 获取作业列表
                task_data = self.get_homework_grading_url(course_url)
                if not task_data:
                    continue

                # 处理每个作业
                for task in task_data:
                    final_results = self.processor.process_homework(
                        task["作业批阅链接"])
                    self.save_result(final_results, task)

            logging.info("作业爬取完成")
            # 关闭浏览器
        self.driver.quit()

    def login(self) -> bool:
        """登录超星学习通

        使用登录策略模式执行登录操作。

        Returns:
            bool: 登录是否成功
        """
        # 使用登录策略执行登录
        login_success = self.login_strategy.login(self.driver)

        if login_success:
            # 获取登录后的 Cookies
            cookies = self.driver.get_cookies()
            self.session_cookies = {
                cookie['name']: cookie['value'] for cookie in cookies}
            logging.info('登录成功，获取到的 Cookies')
            return True
        else:
            logging.error('登录失败')
            return False

    def get_homework_grading_url(self, course_url: str) -> List[Dict[str, Any]]:
        """获取作业列表

        访问课程页面并获取作业列表信息。

        Args:
            course_url: 课程URL

        Returns:
            作业信息列表
        """
        task_data = []
        try:
            # 打开目标网页
            self.driver.get(course_url)
            time.sleep(2)  # 等待页面加载
            # 监听页面的网络请求
            logs = self.driver.get_log("performance")
            list_url = extract_url_from_logs(
                logs,
                "mooc2-ans/work/list",
                "捕获的作业列表请求 URL: "
            )

            if not list_url:
                return task_data

            page_num = 1
            stop_flag = False
            while True:
                if stop_flag:
                    break
                url = convert_url(list_url, page_num)
                response = requests.get(
                    url, headers=self.headers, cookies=self.session_cookies)

                if response.status_code == 200:
                    pass
                else:
                    logging.error(f"请求失败，状态码：{response.status_code}")
                    break
                page_num += 1

                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(response.content, "html.parser")

                # 定位任务的列表 <li> 元素
                tasks = soup.find_all(
                    "li", id=lambda x: x and x.startswith("work"))

                # 遍历每个任务项，提取所需信息
                for task in tasks:
                    # 班级
                    class_name = (
                        task.find("div", class_="list_class").get(
                            "title", "").strip()
                    )
                    if len(self.config.class_list) == 0:
                        pass
                    elif class_name not in self.config.class_list:
                        continue
                    # 提取任务标题
                    title = task.find("h2", class_="list_li_tit").text.strip()
                    if len(self.config.homework_name_list) == 0:
                        pass
                    elif title not in self.config.homework_name_list:
                        continue
                    # 作答时间
                    answer_time = (task.find("p", class_="list_li_time").find(
                        "span").text.strip())
                    # 待批人数
                    pending_review = int(
                        task.find("em", class_="fs28").text.strip())
                    # 提取任务批阅链接
                    review_link = task.find("a", class_="piyueBtn")["href"]
                    # 拼接完整批阅链接
                    homework_grading_url = "https://mooc2-ans.chaoxing.com" + review_link
                    # 大于配置的最小未批改学生数才自动改
                    if pending_review > self.config.min_ungraded_students:
                        # 将提取的数据存入字典
                        task_info = {
                            "班级": class_name,
                            "作答时间": answer_time,
                            "作业名": title,
                            "作业批阅链接": homework_grading_url,
                            "save_path": (
                                "homework/"
                                + sanitize_folder_name(class_name)
                                + "/"
                                + sanitize_folder_name(title + answer_time)
                            )
                        }
                        task_exists = any(
                            t for t in task_data
                            if t["班级"] == task_info["班级"]
                            and t["作答时间"] == task_info["作答时间"]
                            and t["作业名"] == task_info["作业名"]
                        )
                        if task_exists:
                            logging.info("作业已存在，跳过")
                            stop_flag = True
                            break
                        else:
                            # 将任务信息添加到列表
                            task_data.append(task_info)
            return task_data
        except Exception as e:
            logging.error(f'获取作业列表失败：{str(e)}')
            return task_data

    def save_result(self, final_results, task):
        save_path = task["save_path"]
        homework_grading_url = task["作业批阅链接"]
        # 下载作业提交模版
        download(self.driver, self.download_dir,
                 save_path, homework_grading_url)
        # 确保保存目录存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        try:
            # 保存到文件
            file_name = "answer.json"
            with open(os.path.join(save_path, file_name), "w", encoding="utf-8") as f:
                json.dump(final_results, f, indent=4,
                          sort_keys=True, ensure_ascii=False)

            logging.info(f"结果已保存到 {os.path.join(save_path, file_name)}")
        except Exception as e:
            logging.error(f'保存结果失败：{str(e)}')