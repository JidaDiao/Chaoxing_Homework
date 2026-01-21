from crawler.interface import HomeworkProcessor, LoginStrategy, HomeworkCrawler
from crawler.webdriver_factory import WebDriverFactory, WebDriverFactoryCreator
from crawler.login_strategies import LoginStrategyFactory
from bs4 import BeautifulSoup
import requests
import time
import os
import json
import logging
import re
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
from queue import Queue
from utils.tools import *
from crawler.homework_processor_impl import ChaoxingHomeworkProcessor
# 配置日志记录
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
        driver_factory (WebDriverFactory): WebDriver工厂实例
        login_strategy (LoginStrategy): 登录策略实例
        processor (HomeworkProcessor): 作业处理器实例
    """

    @staticmethod
    def create(config: Any, headless: bool = True) -> 'ChaoxingHomeworkCrawler':
        """创建ChaoxingHomeworkCrawler实例

        静态工厂方法，封装WebDriverFactory和LoginStrategy的实例化逻辑，
        简化爬虫实例的创建过程。

        Args:
            config: 配置信息对象
            headless: 是否使用无头模式的WebDriver

        Returns:
            ChaoxingHomeworkCrawler: 爬虫实例
        """
        # 实例化WebDriver工厂
        driver_factory = WebDriverFactoryCreator().create_factory(headless=headless)

        # 实例化登录策略
        use_qr_code = config.use_qr_code if hasattr(
            config, 'use_qr_code') else False
        login_strategy = LoginStrategyFactory.create_strategy(
            use_qr_code, config)

        # 创建并返回爬虫实例
        return ChaoxingHomeworkCrawler(driver_factory, login_strategy, config)

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
        self.processor = None

        # 初始化下载目录
        self.download_dir = self._initialize_download_directory()

        # 初始化WebDriver，使用配置的下载目录
        self.driver = self.driver_factory.create_driver(
            download_dir=self.download_dir)

    def _initialize_download_directory(self) -> str:
        """初始化下载目录

        创建用于保存下载文件的目录。

        Returns:
            str: 下载目录路径
        """
        download_dir = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logging.info(f"创建下载目录: {download_dir}")
        return download_dir

    def run(self) -> None:
        """运行作业爬虫

        执行完整的作业爬取流程，包括登录、获取作业列表和处理作业数据。
        """
        try:
            # 执行登录
            if not self.login():
                logging.error("登录失败，终止爬虫")
                return

            # 获取所有课程的作业批阅链接
            all_homework_tasks = self._get_all_homework_tasks()

            if not all_homework_tasks:
                logging.warning("未找到需要处理的作业")
                return

            logging.info(f"共获取到 {len(all_homework_tasks)} 个作业任务")

            # 创建作业处理器
            self.create_processor()

            # 处理每个作业
            for task_index, task in enumerate(all_homework_tasks, 1):
                logging.info(
                    f"开始处理第 {task_index}/{len(all_homework_tasks)} 个作业: {task['作业名']}")
                self.process_homework(task)

            logging.info("所有作业处理完成")

        except Exception as e:
            logging.error(f"爬虫运行过程中发生错误: {str(e)}")
        finally:
            # 关闭浏览器
            if self.driver:
                self.driver.quit()
                logging.info("已关闭WebDriver")

    def process_homework(self, task: Dict[str, Any]) -> None:
        """处理单个作业

        使用作业处理器处理单个作业任务。

        Args:
            task: 作业任务信息
        """
        try:
            logging.info(f"正在处理作业: {task['作业名']} (班级: {task['班级']})")

            # 使用处理器获取作业数据
            final_results = self.processor.process_homework(task["作业批阅链接"])

            if final_results:
                # 保存处理结果
                self.save_result(final_results, task)
                logging.info(f"作业 '{task['作业名']}' 处理并保存完成")
            else:
                logging.warning(f"作业 '{task['作业名']}' 处理结果为空")

        except Exception as e:
            logging.error(f"处理作业 '{task['作业名']}' 失败: {str(e)}")

    def login(self) -> bool:
        """登录超星学习通

        使用登录策略模式执行登录操作。

        Returns:
            bool: 登录是否成功
        """
        login_url = "https://passport2.chaoxing.com/"
        logging.info("开始登录超星学习通")

        try:
            # 使用登录策略执行登录
            login_success = self.login_strategy.login(self.driver, login_url)

            if login_success:
                # 获取登录后的 Cookies
                cookies = self.driver.get_cookies()
                self.session_cookies = {
                    cookie['name']: cookie['value'] for cookie in cookies
                }
                logging.info('登录成功，已获取Cookie信息')
                return True
            else:
                logging.error('登录失败')
                return False
        except Exception as e:
            logging.error(f"登录过程中发生错误: {str(e)}")
            return False

    def _get_all_homework_tasks(self) -> List[Dict[str, Any]]:
        """获取所有课程的作业批阅链接

        遍历配置的所有课程URL，获取作业批阅链接。

        Returns:
            List[Dict[str, Any]]: 作业批阅链接信息列表
        """
        all_task_data = []

        if not hasattr(self.config, 'course_urls') or not self.config.course_urls:
            logging.warning("配置中未设置课程URL")
            return all_task_data

        logging.info(f"开始获取 {len(self.config.course_urls)} 个课程的作业信息")

        for course_index, course_url in enumerate(self.config.course_urls, 1):
            logging.info(
                f"处理第 {course_index}/{len(self.config.course_urls)} 个课程 URL: {course_url}")

            # 获取作业列表
            task_data = self.get_homework_grading_url(course_url)

            if task_data:
                logging.info(f"从课程中获取到 {len(task_data)} 个作业")
                all_task_data.extend(task_data)
            else:
                logging.warning(f"未在该课程中找到作业")

        logging.info(f"共获取到 {len(all_task_data)} 个作业任务")
        return all_task_data

    def get_homework_grading_url(self, course_url: str) -> List[Dict[str, Any]]:
        """获取作业批阅链接列表

        访问课程页面并获取作业批阅链接列表。

        Args:
            course_url: 课程URL

        Returns:
            List[Dict[str, Any]]: 作业批阅链接信息列表
        """
        task_data = []
        logging.info(f"开始获取课程作业列表: {course_url}")

        try:
            # 打开课程页面
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

            logging.info(f"获取到作业列表URL: {default_list_url}")

            # 如果配置了班级列表，则按班级获取作业
            if hasattr(self.config, 'class_list') and self.config.class_list:
                task_data = self._get_homework_by_classes(default_list_url)
            else:
                # 直接使用默认URL获取作业
                logging.info("未配置班级列表，使用默认URL获取所有作业")
                task_data = self._process_class_homework(default_list_url)

            return task_data

        except Exception as e:
            logging.error(f'获取作业列表失败：{str(e)}')
            return task_data

    def _get_homework_by_classes(self, default_list_url: str) -> List[Dict[str, Any]]:
        """按班级获取作业列表

        获取特定班级的作业列表。

        Args:
            default_list_url: 默认作业列表URL

        Returns:
            List[Dict[str, Any]]: 特定班级的作业信息列表
        """
        task_data = []

        try:
            # 获取页面内容
            response = requests.get(
                default_list_url,
                headers=self.headers,
                cookies=self.session_cookies
            )

            if response.status_code != 200:
                logging.error(f"请求作业列表失败，状态码：{response.status_code}")
                return task_data

            # 解析页面内容
            soup = BeautifulSoup(response.content, "html.parser")

            # 解析班级ID映射
            class_id_map = self._extract_class_id_map(soup)

            if not class_id_map:
                logging.warning("未能提取班级ID映射，将使用默认URL")
                return self._process_class_homework(default_list_url)

            # 处理配置的每个班级
            for class_name in self.config.class_list:
                if class_name in class_id_map:
                    # 构造特定班级的URL
                    class_id = class_id_map[class_name]
                    class_list_url = self._construct_class_url(
                        default_list_url, class_id)
                    logging.info(f"处理班级 '{class_name}' (ID: {class_id}) 的作业列表")

                    # 获取该班级的作业数据
                    class_tasks = self._process_class_homework(class_list_url)
                    task_data.extend(class_tasks)
                else:
                    logging.warning(f"未找到配置的班级: {class_name}")

            return task_data
        except Exception as e:
            logging.error(f"按班级获取作业失败: {str(e)}")
            # 如果获取班级失败，回退到使用默认URL
            logging.info("尝试使用默认URL获取作业")
            return self._process_class_homework(default_list_url)

    def _extract_class_id_map(self, soup: BeautifulSoup) -> Dict[str, str]:
        """从页面中提取班级ID映射

        Args:
            soup: BeautifulSoup解析对象

        Returns:
            Dict[str, str]: 班级名称到ID的映射
        """
        class_id_map = {}

        try:
            # 查找所有班级列表项
            class_items = soup.select("li.classli")

            for item in class_items:
                class_name = item.get('title', '').strip()
                class_id = item.get('data', '')

                if class_name and class_id:
                    class_id_map[class_name] = class_id
                    logging.info(f"找到班级: {class_name}, ID: {class_id}")

            if not class_id_map:
                logging.warning("未找到任何班级信息")

            return class_id_map

        except Exception as e:
            logging.error(f"提取班级ID映射失败: {str(e)}")
            return {}

    def save_result(self, final_results: Dict[str, Any], task: Dict[str, Any]) -> None:
        """保存处理结果

        保存作业处理结果到文件，并下载作业模板。

        Args:
            final_results: 处理后的结果数据
            task: 任务信息，包含保存路径等数据
        """
        save_path = task["save_path"]
        homework_grading_url = task["作业批阅链接"]

        # 确保保存目录存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            logging.info(f"创建保存目录: {save_path}")

        try:
            # 下载作业提交模板（使用导出分数模板的方式）
            # self._download_score_template(homework_grading_url, save_path)
            download_template(self.driver, self.download_dir,
                              save_path, homework_grading_url)

            # 处理不同格式的结果数据
            json_result = final_results

            # 如果final_results是字典并且包含特定键，则提取json结果
            if isinstance(final_results, dict) and "json_result" in final_results:
                json_result = final_results["json_result"]

            # 保存到文件
            file_name = "answer.json"
            file_path = os.path.join(save_path, file_name)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_result, f, indent=4,
                          sort_keys=True, ensure_ascii=False)

            logging.info(f"结果已保存到 {file_path}")

        except Exception as e:
            logging.error(f'保存结果失败：{str(e)}')

    def _construct_class_url(self, default_url: str, class_id: str) -> str:
        """构造特定班级的作业列表URL

        根据默认URL和班级ID构造特定班级的作业列表URL。

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
        """处理特定班级的作业列表

        获取并处理特定班级的作业信息。

        Args:
            list_url: 班级作业列表URL

        Returns:
            List[Dict[str, Any]]: 作业信息列表
        """

        logging.info(f"开始处理班级作业列表: {list_url}")
        tasks = []

        try:
            tasks = self._process_all_pages(list_url, tasks)

            # 处理第一页的作业数据
            class_tasks = self._process_page_tasks(tasks)

            logging.info(f"共获取到 {len(class_tasks)} 个作业任务")
            return class_tasks

        except Exception as e:
            logging.error(f"处理班级作业列表失败: {str(e)}")
            return class_tasks


    def _process_all_pages(self, list_url: str, tasks: List[Dict[str, Any]]) -> None:
        """处理剩余页面

        获取并处理除第一页外的其他页面的作业数据。

        Args:
            list_url: 作业列表URL
            class_tasks: 存储作业信息的列表
        """
        page_num = 1 

        while True:
            # 使用convert_url函数将原始URL转换为新格式并指定页码
            url = convert_url(list_url, page_num)
            logging.info(f"获取第 {page_num} 页作业数据: {url}")

            response = requests.get(
                url, headers=self.headers, cookies=self.session_cookies)

            if response.status_code != 200:
                logging.error(f"请求第{page_num}页失败，状态码：{response.status_code}")
                break

            # 解析HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找作业任务列表
            tasks_ = soup.find_all(
                "li", id=lambda x: x and x.startswith("work"))

            # 如果没有找到任务，说明已经到达最后一页
            if not tasks_:
                logging.info(f"第{page_num}页没有作业任务，翻页结束")
                break

            # 处理当前页的作业任务
            tasks += tasks_

            # 继续下一页
            page_num += 1
        return tasks

    def _process_page_tasks(self, tasks) -> None:
        """处理单页的作业任务列表

        解析并提取单页中的作业信息。

        Args:
            tasks: 当前页面的作业任务列表
        """
        class_tasks = []
        # 遍历每个任务项，提取所需信息
        for task in tasks:
            try:
                # 提取班级名称
                class_name_element = task.find("div", class_="list_class")
                if not class_name_element:
                    continue

                class_name = class_name_element.get("title", "").strip()
                if not class_name:
                    continue

                # 提取任务标题
                title_element = task.find("h2", class_="list_li_tit")
                if not title_element:
                    continue

                title = title_element.text.strip()

                # 如果配置了作业名过滤列表，检查当前作业是否在列表中
                if hasattr(self.config, 'homework_name_list') and self.config.homework_name_list:
                    if title not in self.config.homework_name_list:
                        logging.info(f"作业 '{title}' 不在配置的作业名列表中，跳过")
                        continue

                # 提取作答时间
                time_element = task.find("p", class_="list_li_time")
                if not time_element or not time_element.find("span"):
                    continue

                answer_time = time_element.find("span").text.strip()

                # 提取待批人数
                pending_element = task.find("em", class_="fs28")
                if not pending_element:
                    continue

                pending_review = int(pending_element.text.strip())

                # 检查未批改学生数是否满足最小要求
                if hasattr(self.config, 'min_ungraded_students'):
                    if pending_review <= self.config.min_ungraded_students:
                        logging.info(
                            f"作业 '{title}' 未批改人数 {pending_review} 不满足最小要求 {self.config.min_ungraded_students}，跳过")
                        continue

                # 提取批阅链接
                review_link = task.find("a", class_="piyueBtn")
                if not review_link or "href" not in review_link.attrs:
                    continue

                # 拼接完整批阅链接
                homework_grading_url = "https://mooc2-ans.chaoxing.com" + \
                    review_link["href"]

                # 构造保存路径
                save_path = os.path.join(
                    "homework",
                    sanitize_folder_name(class_name),
                    sanitize_folder_name(title + answer_time)
                )

                # 将提取的数据存入字典
                task_info = {
                    "班级": class_name,
                    "作答时间": answer_time,
                    "作业名": title,
                    "作业批阅链接": homework_grading_url,
                    "save_path": save_path
                }

                # 检查任务是否已存在（避免重复）
                task_exists = any(
                    t for t in class_tasks
                    if t["班级"] == task_info["班级"]
                    and t["作答时间"] == task_info["作答时间"]
                    and t["作业名"] == task_info["作业名"]
                )

                if task_exists:
                    logging.info(f"作业 '{title}' 已存在，跳过")
                else:
                    # 将任务信息添加到列表
                    class_tasks.append(task_info)
                    logging.info(
                        f"添加作业: '{title}' (班级: {class_name}, 待批: {pending_review})")

            except Exception as e:
                logging.error(f"处理作业项失败: {str(e)}")
                continue
        return class_tasks

    def _download_score_template(self, homework_grading_url: str, save_path: str) -> None:
        """下载作业分数导入模板

        下载作业的分数导入Excel模板文件。

        Args:
            homework_grading_url: 作业批阅链接
            save_path: 保存路径
        """
        try:
            # 确保保存目录存在
            if not os.path.exists(save_path):
                os.makedirs(save_path)
                logging.info(f"创建目录: {save_path}")

            # 从批阅链接中提取参数
            params = self._extract_url_params(homework_grading_url)

            if not params:
                logging.error("从批阅链接中提取参数失败")
                return

            work_id = params.get('id', [''])[0]
            class_id = params.get('clazzid', [''])[0]
            course_id = params.get('courseid', [''])[0]
            cpi = params.get('cpi', [''])[0]

            if not all([work_id, class_id, course_id, cpi]):
                logging.error("缺少必要的URL参数")
                return

            # 访问批阅页面获取enc参数
            enc, mooc_import_export_url = self._get_template_parameters(
                homework_grading_url)

            if not enc:
                logging.warning("无法获取模板下载所需的enc参数，将使用空值")

            # 构造下载链接
            download_url = (
                f"{mooc_import_export_url}/export-workscore"
                f"?courseId={course_id}&classId={class_id}&workId={work_id}"
                f"&mooc=1&isTemplate=1&cpi={cpi}&enc={enc}&addLog=true"
            )

            logging.info(f"模板下载URL: {download_url}")

            # 使用requests下载文件
            response = self._download_template_file(download_url, save_path)

            if not response:
                logging.error("下载模板文件失败")

        except Exception as e:
            logging.error(f"下载作业模板失败: {str(e)}")

    def _extract_url_params(self, url: str) -> Dict[str, List[str]]:
        """从URL中提取参数

        Args:
            url: 要解析的URL

        Returns:
            Dict[str, List[str]]: URL参数字典
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            return urllib.parse.parse_qs(parsed_url.query)
        except Exception as e:
            logging.error(f"解析URL参数失败: {str(e)}")
            return {}

    def _get_template_parameters(self, homework_grading_url: str) -> Tuple[str, str]:
        """获取模板下载所需的参数

        从作业批阅页面获取模板下载所需的enc参数和导出URL。

        Args:
            homework_grading_url: 作业批阅链接

        Returns:
            Tuple[str, str]: (enc参数, 导出URL)
        """
        # 访问批阅页面
        self.driver.get(homework_grading_url)
        time.sleep(2)  # 等待页面加载

        enc = ""
        mooc_import_export_url = "https://mooc1.chaoxing.com/mooc-ans"

        try:
            # 尝试从页面中获取enc参数
            enc = self.driver.execute_script(
                "return $('#workScoreExportEnc').val()")
            mooc_url = self.driver.execute_script(
                "return $('#moocImportExportUrl').val()")

            if mooc_url:
                mooc_import_export_url = mooc_url

            if not enc:
                # 如果无法直接获取，尝试从页面源码中提取
                page_source = self.driver.page_source
                enc_match = re.search(
                    r'id="workScoreExportEnc"\s+value="([^"]+)"', page_source)
                url_match = re.search(
                    r'id="moocImportExportUrl"\s+value="([^"]+)"', page_source)

                if enc_match:
                    enc = enc_match.group(1)

                if url_match:
                    mooc_import_export_url = url_match.group(1)

            logging.info(f"获取到模板参数: enc={enc}, url={mooc_import_export_url}")
            return enc, mooc_import_export_url

        except Exception as e:
            logging.error(f"获取模板参数失败: {str(e)}")
            return "", mooc_import_export_url

    def _download_template_file(self, download_url: str, save_path: str) -> Optional[requests.Response]:
        """下载模板文件

        从指定URL下载模板文件并保存到指定目录。

        Args:
            download_url: 下载URL
            save_path: 保存路径

        Returns:
            Optional[requests.Response]: 下载响应
        """
        try:
            # 使用requests下载文件
            response = requests.get(
                download_url,
                headers=self.headers,
                cookies=self.session_cookies,
                stream=True
            )

            if response.status_code != 200:
                logging.error(f"下载模板失败，状态码: {response.status_code}")
                return None

            # 从Content-Disposition获取文件名
            file_extension = self._get_file_extension(response)
            filename = f"template{file_extension}"
            file_path = os.path.join(save_path, filename)

            # 保存文件
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logging.info(f"模板已下载到: {file_path}")
            return response

        except Exception as e:
            logging.error(f"下载模板文件失败: {str(e)}")
            return None

    def _get_file_extension(self, response: requests.Response) -> str:
        """从响应头中获取文件扩展名

        Args:
            response: HTTP响应对象

        Returns:
            str: 文件扩展名
        """
        try:
            content_disposition = response.headers.get(
                'Content-Disposition', '')
            filename_match = re.search(
                r'filename="?([^";]+)"?', content_disposition)

            if filename_match:
                # 获取原始文件名的后缀
                original_filename = filename_match.group(1)
                file_extension = os.path.splitext(original_filename)[1]
                return file_extension
            else:
                return '.xls'  # 默认扩展名
        except Exception:
            return '.xls'  # 出错时使用默认扩展名

    def create_processor(self) -> None:
        """创建作业处理器

        初始化作业处理器实例。
        """
        self.processor = ChaoxingHomeworkProcessor(
            driver=self.driver,
            session_cookies=self.session_cookies,
            headers=self.headers,
            driver_queue=self.driver_queue,
            config=self.config
        )
        logging.info("已创建作业处理器")
