from bs4 import BeautifulSoup
from typing import Dict, List, Any
import requests
import logging
from .base import DataProcessor
from utils.tools import sanitize_folder_name
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
class HomeworkDataProcessor(DataProcessor):
    """作业数据处理策略类
    
    实现作业列表数据的处理逻辑。
    """
    def __init__(self, headers: Dict, session_cookies: Dict, config: Any):
        self.headers = headers
        self.session_cookies = session_cookies
        self.config = config

    def select_class(self, driver, class_name: str) -> bool:
        """选择指定班级
        
        Args:
            driver: WebDriver实例
            class_name: 要选择的班级名称
            
        Returns:
            bool: 是否成功选择班级
        """
        try:
            # 点击班级选择框
            class_select = driver.find_element('css selector', '.banji_select_name')
            class_select.click()
            
            # 等待班级列表加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(('css selector', '.banji_list'))
            )
            
            # 查找并点击目标班级
            class_items = driver.find_elements('css selector', '.classli')
            for item in class_items:
                if class_name in item.get_attribute('title'):
                    item.click()
                    return True
            return False
        except Exception as e:
            logging.error(f'选择班级失败：{str(e)}')
            return False

    def process(self, data: Dict) -> Dict:
        task_data = []
        try:
            if not self.select_class(data['driver'], data['target_class']):
                logging.error(f'未找到目标班级：{data["target_class"]}')
                return task_data
            # 等待页面刷新
            time.sleep(1)
            # 监听页面的网络请求
            logs = self.driver.get_log("performance")
            list_url = self._get_url_from_logs(
                logs,
                "mooc2-ans/work/list",
                "捕获的作业列表请求 URL: "
            )
            # 获取更新后的页面内容
            content = data['driver'].page_source
            soup = BeautifulSoup(content, 'html.parser')
            tasks = soup.find_all('li', id=lambda x: x and x.startswith('work'))

            for task in tasks:
                # 提取班级信息
                class_name = task.find('div', class_='list_class').get('title', '').strip()
                if len(self.config.class_list) > 0 and class_name not in self.config.class_list:
                    continue

                # 提取作业标题
                title = task.find('h2', class_='list_li_tit').text.strip()
                if len(self.config.homework_name_list) > 0 and title not in self.config.homework_name_list:
                    continue

                # 提取作答时间
                answer_time = task.find('p', class_='list_li_time').find('span').text.strip()
                
                # 提取待批人数
                pending_review = int(task.find('em', class_='fs28').text.strip())
                
                # 提取批阅链接
                review_link = task.find('a', class_='piyueBtn')['href']
                piyue_url = 'https://mooc2-ans.chaoxing.com' + review_link

                if pending_review > self.config.min_ungraded_students:
                    task_info = {
                        '班级': class_name,
                        '作答时间': answer_time,
                        '作业名': title,
                        'review_link': piyue_url,
                    }
                    task_data.append(task_info)

            return task_data
        except Exception as e:
            logging.error(f'处理作业列表数据失败：{str(e)}')
            return task_data

class StudentAnswerProcessor(DataProcessor):
    """学生答案处理策略类
    
    实现学生答案数据的处理逻辑。
    """
    def __init__(self, headers: Dict, session_cookies: Dict):
        self.headers = headers
        self.session_cookies = session_cookies

    def process(self, data: Dict) -> Dict:
        try:
            response = requests.get(
                data['url'],
                headers=self.headers,
                cookies=self.session_cookies
            )
            soup = BeautifulSoup(response.content, 'html.parser')
            all_questions = []
            question_blocks = soup.find_all('div', class_='mark_item1')

            for block in question_blocks:
                # 提取题目描述
                question_description = block.find('div', class_='hiddenTitle').text.strip()

                # 提取学生答案
                student_answer_tag = block.find(
                    'dl',
                    class_='mark_fill',
                    id=lambda x: x and x.startswith('stuanswer_')
                )
                
                if student_answer_tag:
                    text_answers = [
                        p.text.strip()
                        for p in student_answer_tag.find_all('p')
                        if p.text.strip()
                    ]
                    image_answers = [
                        img['src']
                        for img in student_answer_tag.find_all('img')
                        if 'src' in img.attrs
                    ]
                    student_answer = {'text': text_answers, 'images': image_answers}
                else:
                    student_answer = {'text': [], 'images': []}

                # 提取参考答案
                correct_answer_tag = block.find(
                    'dl',
                    class_='mark_fill',
                    id=lambda x: x and x.startswith('correctanswer_')
                )
                correct_answer = correct_answer_tag.text.strip() if correct_answer_tag else '此题无参考答案'

                question_data = {
                    'description': question_description,
                    'student_answer': student_answer,
                    'correct_answer': correct_answer.replace('参考答案：', '', 1)
                }
                all_questions.append(question_data)

            return all_questions
        except Exception as e:
            logging.error(f'处理学生答案数据失败：{str(e)}')
            return []

class DataProcessorFactory:
    """数据处理策略工厂类
    
    用于创建不同的数据处理策略实例。
    """
    @staticmethod
    def create_processor(processor_type: str, headers: Dict, session_cookies: Dict, config: Any = None) -> DataProcessor:
        """创建数据处理策略
        
        Args:
            processor_type: 处理器类型
            headers: HTTP请求头
            session_cookies: 会话Cookie
            config: 配置对象
            
        Returns:
            DataProcessor: 数据处理策略实例
        """
        if processor_type == 'homework':
            return HomeworkDataProcessor(headers, session_cookies, config)
        elif processor_type == 'student_answer':
            return StudentAnswerProcessor(headers, session_cookies)
        else:
            raise ValueError(f'不支持的处理器类型：{processor_type}')