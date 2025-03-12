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
# 配置logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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

        # 初始化WebDriver
        self.driver = self.driver_factory.create_driver()

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
            task_data = self._get_homework_all_grading_url()
            self.create_processer()

            # 处理每个作业
            for task in task_data:
                self.process_homework(task)

            logging.info("作业爬取完成")
            # 关闭浏览器
        self.driver.quit()

    def process_homework(self, task):
        final_results = self.processor.process_homework(task["作业批阅链接"])
        self.save_result(final_results, task)

    def login(self) -> bool:
        """登录超星学习通

        使用登录策略模式执行登录操作。

        Returns:
            bool: 登录是否成功
        """
        loginurl = "https://passport2.chaoxing.com/"
        # 使用登录策略执行登录
        login_success = self.login_strategy.login(self.driver, loginurl)

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

    def _get_homework_all_grading_url(self) -> List[Dict[str, Any]]:
        all_task_data = []
        for course_url in self.config.course_urls:
            # 获取作业列表
            task_data = self.get_homework_grading_url(course_url)
            if task_data:
                all_task_data.extend(task_data)
        return all_task_data

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

            # 获取默认作业列表URL
            logs = self.driver.get_log("performance")
            default_list_url = extract_url_from_logs(
                logs,
                "mooc2-ans/work/list",
                "捕获的作业列表请求 URL: "
            )

            if not default_list_url:
                logging.error("未能捕获到作业列表URL")
                return task_data
            else:
                response = requests.get(
                    default_list_url, headers=self.headers, cookies=self.session_cookies)
                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(response.content, "html.parser")

            # 如果配置了班级列表，则尝试获取每个班级的作业列表
            if len(self.config.class_list) > 0:
                # 解析页面获取班级ID映射
                class_id_map = {}
                try:
                    # 查找所有班级列表项
                    # 使用 select 方法替代 find_elements
                    class_items = soup.select("li.classli")
                    for item in class_items:
                        class_name = item.get(
                            'title', '').strip()  # 使用 get 方法获取属性
                        class_id = item.get('data', '')  # 使用 get 方法获取属性
                        class_id_map[class_name] = class_id

                    # 处理每个配置的班级
                    for class_name in self.config.class_list:
                        if class_name in class_id_map:
                            # 构造特定班级的URL
                            class_id = class_id_map[class_name]
                            class_list_url = self._construct_class_url(
                                default_list_url, class_id)
                            logging.info(
                                f"处理班级 '{class_name}' (ID: {class_id}) 的作业列表")

                            # 获取该班级的作业数据
                            class_tasks = self._process_class_homework(
                                class_list_url)
                            task_data.extend(class_tasks)
                        else:
                            logging.warning(f"未找到配置的班级: {class_name}")
                except Exception as e:
                    logging.error(f"获取班级信息失败: {str(e)}")
                    # 如果获取班级失败，回退到使用默认URL
                    task_data.extend(
                        self._process_class_homework(default_list_url))
            else:
                # 如果没有配置班级列表，使用默认URL
                task_data.extend(
                    self._process_class_homework(default_list_url))

            return task_data
        except Exception as e:
            logging.error(f'获取作业列表失败：{str(e)}')
            return task_data

    def save_result(self, final_results, task):
        save_path = task["save_path"]
        homework_grading_url = task["作业批阅链接"]

        # 下载作业提交模版（使用导出分数模板的方式）
        self._download_score_template(homework_grading_url, save_path)

        # 确保保存目录存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        try:
            # 处理不同格式的结果数据
            json_result = final_results
            db_result = final_results
            
            # 如果final_results是字典并且包含特定键，则分别提取json和db结果
            if isinstance(final_results, dict) and "json_result" in final_results and "db_result" in final_results:
                json_result = final_results["json_result"]
                db_result = final_results["db_result"]
            
            # 保存到文件
            file_name = "answer.json"
            with open(os.path.join(save_path, file_name), "w", encoding="utf-8") as f:
                json.dump(json_result, f, indent=4,
                          sort_keys=True, ensure_ascii=False)

            logging.info(f"结果已保存到 {os.path.join(save_path, file_name)}")
            
            # 保存到SQLite数据库
            try:
                from utils.db_manager import DatabaseManager
                db_manager = DatabaseManager()
                db_manager.save_homework_data(task, db_result)
                logging.info("结果已保存到SQLite数据库")
                db_manager.close()
            except Exception as db_error:
                logging.error(f'保存到数据库失败：{str(db_error)}')
        except Exception as e:
            logging.error(f'保存结果失败：{str(e)}')

    def _construct_class_url(self, default_url: str, class_id: str) -> str:
        """
        根据默认URL和班级ID构造特定班级的作业列表URL

        Args:
            default_url: 默认的作业列表URL
            class_id: 班级ID

        Returns:
            str: 特定班级的作业列表URL
        """
        # 解析URL
        if "selectClassid=" in default_url:
            # 替换selectClassid参数
            return re.sub(r'selectClassid=\d+', f'selectClassid={class_id}', default_url)
        else:
            # 添加selectClassid参数
            if "?" in default_url:
                return f"{default_url}&selectClassid={class_id}"
            else:
                return f"{default_url}?selectClassid={class_id}"

    def _process_class_homework(self, list_url: str) -> List[Dict[str, Any]]:
        """
        处理特定班级的作业列表

        Args:
            list_url: 班级作业列表URL

        Returns:
            List[Dict[str, Any]]: 作业信息列表
        """
        class_tasks = []
        page_num = 1
        stop_flag = False
        has_more_pages = True

        # 首先检查是否需要翻页
        # 获取第一页数据

        response = requests.get(
            list_url, headers=self.headers, cookies=self.session_cookies)

        if response.status_code != 200:
            logging.error(f"请求失败，状态码：{response.status_code}")
            return class_tasks

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # 检查是否有分页元素
        pagination = soup.find("div", class_="page")
        if pagination and pagination.find_all("a"):
            logging.info("检测到作业列表有多页，将进行翻页获取")
            has_more_pages = True
        else:
            has_more_pages = False

        # 处理第一页数据
        tasks = soup.find_all("li", id=lambda x: x and x.startswith("work"))
        if not tasks:
            logging.info("未找到任何作业任务")
            return class_tasks

        # 处理第一页的作业数据
        self._process_page_tasks(tasks, class_tasks, stop_flag)

        # 如果需要翻页且第一页处理没有触发停止标志，则继续处理后续页面
        page_num = 2  # 从第二页开始

        while has_more_pages and not stop_flag:
            url = convert_url(list_url, page_num)
            response = requests.get(
                url, headers=self.headers, cookies=self.session_cookies)

            if response.status_code != 200:
                logging.error(f"请求第{page_num}页失败，状态码：{response.status_code}")
                break

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # 定位任务的列表 <li> 元素
            tasks = soup.find_all(
                "li", id=lambda x: x and x.startswith("work"))

            # 如果没有找到任务，说明已经到达最后一页
            if not tasks:
                logging.info(f"第{page_num}页没有作业任务，翻页结束")
                break

            # 处理当前页的作业任务
            self._process_page_tasks(tasks, class_tasks, stop_flag)

            # 检查是否需要继续翻页
            page_num += 1

        return class_tasks

    def _process_page_tasks(self, tasks, class_tasks, stop_flag):
        """处理单页的作业任务列表

        Args:
            tasks: 当前页面的作业任务列表
            class_tasks: 存储作业信息的列表
            stop_flag: 停止标志

        Returns:
            bool: 是否需要停止处理
        """
        # 遍历每个任务项，提取所需信息
        for task in tasks:
            # 班级
            class_name = (
                task.find("div", class_="list_class").get(
                    "title", "").strip()
            )

            # 提取任务标题
            title = task.find("h2", class_="list_li_tit").text.strip()
            if len(self.config.homework_name_list) > 0 and title not in self.config.homework_name_list:
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
                    t for t in class_tasks
                    if t["班级"] == task_info["班级"]
                    and t["作答时间"] == task_info["作答时间"]
                    and t["作业名"] == task_info["作业名"]
                )

                if task_exists:
                    logging.info("作业已存在，跳过")
                    return True
                else:
                    # 将任务信息添加到列表
                    class_tasks.append(task_info)

        return False

        return class_tasks

    def _download_score_template(self, homework_grading_url: str, save_path: str):
        """
        下载作业分数导入模板

        Args:
            homework_grading_url: 作业批阅链接
            save_path: 保存路径
        """
        try:
            # 确保保存目录存在
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # 从批阅链接中提取参数
            import re
            import urllib.parse

            # 提取URL中的参数
            parsed_url = urllib.parse.urlparse(homework_grading_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # 获取必要参数
            work_id = query_params.get('id', [''])[0]
            class_id = query_params.get('clazzid', [''])[0]
            course_id = query_params.get('courseid', [''])[0]
            cpi = query_params.get('cpi', [''])[0]

            # 访问批阅页面获取enc参数
            self.driver.get(homework_grading_url)
            time.sleep(2)  # 等待页面加载

            # 尝试从页面中获取enc参数
            try:
                enc = self.driver.execute_script(
                    "return $('#workScoreExportEnc').val()")
                mooc_import_export_url = self.driver.execute_script(
                    "return $('#moocImportExportUrl').val()")

                if not enc or not mooc_import_export_url:
                    # 如果无法获取，尝试从页面源码中提取
                    page_source = self.driver.page_source
                    enc_match = re.search(
                        r'id="workScoreExportEnc"\s+value="([^"]+)"', page_source)
                    url_match = re.search(
                        r'id="moocImportExportUrl"\s+value="([^"]+)"', page_source)

                    enc = enc_match.group(1) if enc_match else ""
                    mooc_import_export_url = url_match.group(
                        1) if url_match else "https://mooc1.chaoxing.com/mooc-ans"
            except Exception as e:
                logging.error(f"获取enc参数失败: {str(e)}")
                enc = ""
                mooc_import_export_url = "https://mooc1.chaoxing.com/mooc-ans"

            # 构造下载链接
            download_url = (
                f"{mooc_import_export_url}/export-workscore"
                f"?courseId={course_id}&classId={class_id}&workId={work_id}"
                f"&mooc=1&isTemplate=1&cpi={cpi}&enc={enc}&addLog=true"
            )

            logging.info(f"下载模板URL: {download_url}")

            # 使用requests下载文件
            response = requests.get(
                download_url,
                headers=self.headers,
                cookies=self.session_cookies,
                stream=True
            )

            if response.status_code == 200:
                # 从Content-Disposition获取文件名后缀
                content_disposition = response.headers.get(
                    'Content-Disposition', '')
                filename_match = re.search(
                    r'filename="?([^";]+)"?', content_disposition)

                if filename_match:
                    # 获取原始文件名的后缀
                    original_filename = filename_match.group(1)
                    file_extension = os.path.splitext(original_filename)[1]
                else:
                    file_extension = '.xls'

                # 使用template作为文件名
                filename = f"template{file_extension}"

                # 保存文件
                file_path = os.path.join(save_path, filename)
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                logging.info(f"模板已下载到: {file_path}")
            else:
                logging.error(f"下载模板失败，状态码: {response.status_code}")

        except Exception as e:
            logging.error(f"下载作业模板失败: {str(e)}")
    def create_processer(self):
        # 初始化处理器
        self.processor = ChaoxingHomeworkProcessor(
            driver=self.driver,
            session_cookies=self.session_cookies,
            headers=self.headers,
            driver_queue=self.driver_queue,
            config=self.config
        )
