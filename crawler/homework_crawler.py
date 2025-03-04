from selenium import webdriver
from typing import Dict, List, Optional
from queue import Queue
import threading
import os
import time
import logging
import json
from crawler.base import WebDriverBuilder
from crawler.login_strategies import LoginStrategyFactory
from concurrent.futures import ThreadPoolExecutor
from crawler.data_processors import DataProcessorFactory
from utils.tools import download, sanitize_folder_name
from config.args import config

class HomeworkCrawler:
    """超星学习通作业爬虫类
    
    使用设计模式重构的爬虫主类，整合了所有爬虫功能。
    """
    def __init__(self, chrome_driver_path: str):
        self.chrome_driver_path = chrome_driver_path
        self.driver = None
        self.driver_queue = Queue()
        self.session_cookies = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
        }
        self._init_driver()

    def _init_driver(self) -> None:
        """初始化WebDriver
        
        使用建造者模式初始化Chrome WebDriver。
        """
        download_dir = os.path.join(os.getcwd(), 'downloads')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        self.download_dir = download_dir

        builder = WebDriverBuilder()
        self.driver = builder\
            .set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0')\
            .set_download_dir(download_dir)\
            .set_headless(True)\
            .build(self.chrome_driver_path)



    def login(self) -> bool:
        """登录超星学习通
        
        使用工厂模式创建登录策略并执行登录。
        
        Returns:
            bool: 登录是否成功
        """
        try:
            login_url = 'https://passport2.chaoxing.com/'
            self.driver.get(login_url)
            logging.info('打开登录页面')

            login_strategy = LoginStrategyFactory.create_strategy(config.use_qr_code)
            if login_strategy.login(self.driver):
                cookies = self.driver.get_cookies()
                self.session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                logging.info('登录成功')
                return True
            else:
                logging.error('登录失败')
                return False
        except Exception as e:
            logging.error(f'登录过程发生错误：{str(e)}')
            return False

    def get_homework_list(self, course_url: str) -> List[Dict]:
        """获取作业列表
        
        使用策略模式处理作业列表数据。
        
        Args:
            course_url: 课程URL
            
        Returns:
            List[Dict]: 作业信息列表
        """
        try:
            self.driver.get(course_url)
            time.sleep(2)
            # 监听页面的网络请求
            _ = self.driver.get_log("performance")

            processor = DataProcessorFactory.create_processor(
                'homework',
                self.headers,
                self.session_cookies,
                config
            )
            return processor.process({'driver': self.driver,'target_class':config.class_list})
        except Exception as e:
            logging.error(f'获取作业列表失败：{str(e)}')
            return []

    def process_homework(self, task: Dict) -> None:
        """处理单个作业
        
        处理单个作业的数据，包括下载分数提交模版和抓取学生答案。
        
        Args:
            task: 作业信息字典
        """
        try:
            save_path = (
                'homework/'
                + sanitize_folder_name(task['班级'])
                + '/'
                + sanitize_folder_name(task['作业名'] + task['作答时间'])
            )
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            else:
                return

            # 下载分数提交模版
            download(self.driver, self.download_dir, save_path, task['review_link'])

            # 获取并处理学生数据
            student_data = self._get_student_data(task['review_link'])
            if student_data:
                task_list = self._process_student_answers(student_data)
                if task_list:
                    self._save_results(task_list, save_path, 'answer.json')

        except Exception as e:
            logging.error(f'处理作业失败：{str(e)}')

    def _get_student_data(self, review_url: str) -> List[Dict]:
        """获取学生数据
        
        Args:
            review_url: 批阅页面URL
            
        Returns:
            List[Dict]: 学生数据列表
        """
        try:
            self.driver.get(review_url)
            time.sleep(2)

            processor = DataProcessorFactory.create_processor(
                'student_answer',
                self.headers,
                self.session_cookies
            )
            return processor.process({'url': review_url})
        except Exception as e:
            logging.error(f'获取学生数据失败：{str(e)}')
            return []

    def _process_student_answers(self, student_data: List[Dict]) -> Dict:
        """处理学生答案
        
        使用多线程处理所有学生的答案数据。
        
        Args:
            student_data: 学生数据列表
            
        Returns:
            Dict: 处理后的学生答案字典
        """
        task_list = {}
        try:
            num_threads = config.max_workers_prepare
            if self.driver_queue.empty():
                for _ in range(num_threads):
                    builder = WebDriverBuilder()
                    driver = builder\
                        .set_headless(True)\
                        .build(self.chrome_driver_path)
                    self.driver_queue.put(driver)

            task_list_lock = threading.Lock()

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for student in student_data:
                    future = executor.submit(
                        self._process_single_student,
                        student,
                        task_list_lock,
                        task_list
                    )
                    futures.append(future)

                for future in futures:
                    future.result()

            return task_list
        except Exception as e:
            logging.error(f'处理学生答案失败：{str(e)}')
            return task_list

    def _process_single_student(self, student: Dict, task_list_lock: threading.Lock,
                              task_list: Dict) -> None:
        """处理单个学生的答案
        
        Args:
            student: 学生信息
            task_list_lock: 线程锁
            task_list: 答案字典
        """
        driver = self.driver_queue.get()
        try:
            processor = DataProcessorFactory.create_processor(
                'student_answer',
                self.headers,
                self.session_cookies
            )
            result = processor.process({'url': student['review_link']})

            with task_list_lock:
                task_list[student['name']] = result
        finally:
            self.driver_queue.put(driver)

    def _save_results(self, data: Dict, save_path: str, file_name: str) -> None:
        """保存结果
        
        Args:
            data: 要保存的数据
            save_path: 保存路径
            file_name: 文件名
        """
        try:
            file_path = os.path.join(save_path, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f'结果已保存到：{file_path}')
        except Exception as e:
            logging.error(f'保存结果失败：{str(e)}')

    def run(self) -> None:
        """运行爬虫
        
        执行完整的作业爬取流程。
        """
        if not self.login():
            return

        for course_url in config.course_urls:
            task_data = self.get_homework_list(course_url)
            if task_data:
                for task in task_data:
                    self.process_homework(task)

        logging.info('作业爬取完成')
        self.driver.quit()