import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading
import os
from utils import *
from config.args import config
import logging

# 配置logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class HomeworkCrawler:
    """超星学习通作业爬虫类

    该类整合了作业爬取的所有功能，包括登录、获取课程链接、解析作业列表、下载作业数据等。
    使用Selenium进行页面操作，支持多线程并行处理以提高效率。

    Attributes:
        driver (webdriver.Chrome): Chrome浏览器驱动实例
        driver_queue (Queue): WebDriver实例队列，用于多线程处理
        session_cookies (dict): 会话Cookie信息
        headers (dict): HTTP请求头信息
    """

    def __init__(self, chrome_driver_path):
        """初始化作业爬虫

        初始化HomeworkCrawler类的实例，设置必要的属性和WebDriver配置。

        Args:
            chrome_driver_path (str): Chrome驱动程序的路径

        Returns:
            None
        """
        self.driver = None
        self.driver_queue = Queue()
        self.session_cookies = None
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
                        }
        self._init_driver(chrome_driver_path)

    def _init_driver(self, chrome_driver_path):
        """初始化Chrome WebDriver

        设置并初始化Chrome WebDriver，配置浏览器选项和性能日志捕获。

        Args:
            chrome_driver_path (str): Chrome驱动程序的路径

        Returns:
            None
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0")
        options.headless = True

        download_dir = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        self.download_dir = download_dir

        # 设置下载目录
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)

        caps = DesiredCapabilities.CHROME
        caps["goog:loggingPrefs"] = {"performance": "ALL"}
        options.set_capability("goog:loggingPrefs", caps["goog:loggingPrefs"])

        service = Service(chrome_driver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

    def _get_url_from_logs(self, logs, url_pattern, log_message=""):
        """从浏览器性能日志中获取特定URL

        Args:
            logs (list): 浏览器性能日志列表
            url_pattern (str): URL匹配模式
            log_message (str): 日志消息，默认为空

        Returns:
            str: 匹配到的URL，如果未找到则返回None
        """
        target_url = None
        for log in logs:
            message = log["message"]
            if url_pattern in message:
                log_json = json.loads(message)["message"]["params"]
                if "request" in log_json and "url" in log_json["request"]:
                    target_url = log_json["request"]["url"]
                    if log_message:
                        logging.info(log_message + target_url)
                    break
        return target_url

    def process_student(
        self, student, headers, session_cookies, driver_queue, task_list_lock, task_list
    ):
        """处理单个学生的作业数据

        获取并处理单个学生的作业答案，包括文本答案和图片答案。

        Args:
            student (dict): 学生信息，包含姓名和作业链接
            headers (dict): HTTP请求头
            session_cookies (dict): 会话Cookie
            driver_queue (Queue): WebDriver实例队列
            task_list_lock (threading.Lock): 线程锁
            task_list (dict): 存储所有学生答案的字典

        Returns:
            None
        """
        # 从队列中获取driver
        driver = driver_queue.get()
        try:
            student_name = student["name"]
            student_url = student["review_link"]
            driver.get(student_url)
            time.sleep(2)

            logs = driver.get_log("performance")
            target_url = self._get_url_from_logs(
                logs,
                "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work",
                "捕获的学生作答内容的 URL: "
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
                    if question_description_tag:
                        question_description = question_description_tag.text.strip()
                    else:
                        logging.error("未找到题目描述")

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
            for course_url in config.course_urls:
                # 获取作业列表
                task_data = self.get_homework_list(course_url)
                if not task_data:
                    continue

                # 处理每个作业
                for task in task_data:
                    self.process_homework(task)

            logging.info("作业爬取完成")
            # 关闭浏览器
        self.driver.quit()

    def login(self):
        """登录超星学习通

        使用Selenium模拟登录超星学习通，支持账号密码登录和扫码登录两种方式。

        Args:
            use_qr_code (bool): 是否使用扫码登录，默认为False使用账号密码登录

        Returns:
            bool: 登录是否成功
        """
        loginurl = "https://passport2.chaoxing.com/"
        # 打开登录页面
        self.driver.get(loginurl)
        logging.info('打开登录页面')

        if config.use_qr_code:
            try:
                # 等待二维码元素出现
                _ = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "quickCode"))
                )
                logging.info('请使用超星学习通APP扫描二维码登录')

                # 等待登录成功（通过检测URL变化判断）
                WebDriverWait(self.driver, 300).until(
                    lambda driver: "passport2.chaoxing.com" not in driver.current_url
                )
                logging.info('扫码登录成功')
            except Exception as e:
                logging.error(f'扫码登录失败：{str(e)}')
                return False
        else:
            try:
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="phone"]'))
                )

                # 输入手机号和密码
                phonenumber = config.phonenumber
                password = config.password

                self.driver.find_element(
                    By.XPATH, '//*[@id="phone"]').send_keys(phonenumber)
                self.driver.find_element(
                    By.XPATH, '//*[@id="pwd"]').send_keys(password)

                # 点击登录按钮
                self.driver.find_element(By.XPATH, '//*[@id="loginBtn"]').click()

                # 等待登录完成
                time.sleep(2)
            except Exception as e:
                logging.error(f'账号密码登录失败：{str(e)}')
                return False

        # 获取登录后的 Cookies
        cookies = self.driver.get_cookies()
        self.session_cookies = {cookie['name']: cookie['value']
                                for cookie in cookies}
        if len(cookies) > 6:
            logging.info('登录成功，获取到的 Cookies')
            return True
        else:
            logging.error('登录失败')
            return False

    def get_homework_list(self, course_url):
        """获取作业列表

        访问课程页面并获取作业列表信息。

        Args:
            course_url (str): 课程URL

        Returns:
            list: 作业信息列表
        """
        task_data = []
        try:
            # 打开目标网页
            self.driver.get(course_url)
            time.sleep(2)  # 等待页面加载
            # 监听页面的网络请求
            logs = self.driver.get_log("performance")
            list_url = self._get_url_from_logs(
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
                    logging.info("作业列表请求成功!")
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
                    if len(config.class_list) == 0:
                        pass
                    elif class_name not in config.class_list:
                        continue
                    # 提取任务标题
                    title = task.find("h2", class_="list_li_tit").text.strip()
                    # 作答时间
                    answer_time = (task.find("p", class_="list_li_time").find(
                        "span").text.strip())
                    # 待批人数
                    pending_review = int(
                        task.find("em", class_="fs28").text.strip())
                    # 提取任务批阅链接
                    review_link = task.find("a", class_="piyueBtn")["href"]
                    # 拼接完整批阅链接
                    piyue_url = "https://mooc2-ans.chaoxing.com" + review_link
                    # 大于5个学生要改才自动改
                    if pending_review > config.min_ungraded_students:
                        # 将提取的数据存入字典
                        task_info = {
                            "班级": class_name,
                            "作答时间": answer_time,
                            "作业名": title,
                            "review_link": piyue_url,
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

    def process_homework(self, task):
        """处理单个作业

        处理单个作业的数据，包括下载分数提交模版和抓取学生答案。

        Args:
            task (dict): 作业信息字典

        Returns:
            None
        """
        try:
            save_path = (
                "homework/"
                + sanitize_folder_name(task["班级"])
                + "/"
                + sanitize_folder_name(task["作业名"] + task["作答时间"])
            )
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            else:
                return

            piyue_url = task["review_link"]
            file_name = "answer.json"
            logging.info("当前批阅链接：" + piyue_url)
            # 下载分数提交模版
            download(self.driver, self.download_dir, save_path, piyue_url)

            # 获取学生数据
            student_data = self._get_student_data(piyue_url)
            if not student_data:
                return

            # 抓取学生答案
            task_list = self._process_student_answers(student_data)
            if not task_list:
                return

            # 保存结果
            self._save_results(task_list, save_path, file_name)

        except Exception as e:
            logging.error(f'处理作业失败：{str(e)}')

    def _get_student_data(self, piyue_url):
        """获取学生数据

        从批阅页面获取学生的答案数据列表。

        Args:
            piyue_url (str): 批阅页面URL

        Returns:
            list: 学生数据列表
        """
        student_data = []
        self.driver.get(piyue_url)
        time.sleep(2)  # 等待页面加载
        try:
            logs = self.driver.get_log("performance")
            target_url = self._get_url_from_logs(
                logs,
                "mooc2-ans/work/mark-list",
                "捕获的目标批阅列表请求 URL: "
            )

            target_url = re.sub(r"pages=\d+", "pages={}", target_url)
            final_page_num = 1

            while True:
                target_url_modified = target_url.format(final_page_num)
                response = requests.get(
                    target_url_modified,
                    headers=self.headers,
                    cookies=self.session_cookies,
                )

                if response.status_code == 200:
                    logging.info("最终批阅链接请求成功!")
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

    def _process_student_answers(self, student_data):
        """处理学生答案

        使用多线程处理所有学生的答案数据。

        Args:
            student_data (list): 学生数据列表

        Returns:
            dict: 处理后的学生答案字典
        """
        task_list = {}
        try:
            # 创建多个WebDriver实例
            num_threads = config.max_workers_prepare
            if self.driver_queue.empty():
                for _ in range(num_threads):
                    options = webdriver.ChromeOptions()
                    driver_ = webdriver.Chrome(
                        service=Service(config.chrome_driver_path),
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
                        self.process_student,
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

    def _save_results(self, task_list, save_path, file_name):
        """保存处理结果

        将处理后的学生答案保存到JSON文件。

        Args:
            task_list (dict): 处理后的学生答案字典
            save_path (str): 保存路径
            file_name (str): 文件名

        Returns:
            None
        """
        try:
            final_list = {
                "题目": {},
                "学生回答": {}
            }

            student_name_list = list(task_list.keys())
            len_task = len(task_list[student_name_list[0]])

            # 初始化学生回答字典
            for student_name in student_name_list:
                final_list["学生回答"][student_name] = {}

            # 处理每道题目
            for i in range(len_task):
                question_key = "题目" + str(i + 1)
                final_list["题目"][question_key] = {
                    "题干": task_list[student_name_list[0]][i]["description"],
                    "正确答案": task_list[student_name_list[0]][i]["correct_answer"]
                }
                for student_name in student_name_list:
                    final_list["学生回答"][student_name][question_key] = \
                        task_list[student_name][i]["student_answer"]

            # 保存到文件
            with open(os.path.join(save_path, file_name), "w", encoding="utf-8") as f:
                json.dump(final_list, f, indent=4,
                          sort_keys=True, ensure_ascii=False)

        except Exception as e:
            logging.error(f'保存结果失败：{str(e)}')
