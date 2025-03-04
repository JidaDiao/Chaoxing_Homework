from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from typing import Dict, List, Any, Optional
from queue import Queue
import threading
import os
import time
import logging
from .login_strategies import LoginStrategyFactory
from config.args import config

class HomeworkCrawler:
    """超星学习通作业爬虫类
    
    使用策略模式重构的爬虫主类，整合了所有爬虫功能。
    """
    def __init__(self, chrome_driver_path: str):
        """初始化作业爬虫
        
        Args:
            chrome_driver_path: Chrome驱动程序路径
        """
        self.driver = None
        self.driver_queue = Queue()
        self.session_cookies = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
        }
        self._init_driver(chrome_driver_path)
    
    def _init_driver(self, chrome_driver_path: str) -> None:
        """初始化Chrome WebDriver
        
        Args:
            chrome_driver_path: Chrome驱动程序路径
        """
        options = ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
        )
        options.headless = True

        download_dir = os.path.join(os.getcwd(), 'downloads')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        self.download_dir = download_dir

        prefs = {
            'download.default_directory': download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True
        }
        options.add_experimental_option('prefs', prefs)

        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        options.set_capability('goog:loggingPrefs', caps['goog:loggingPrefs'])

        service = Service(chrome_driver_path)
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def login(self) -> bool:
        """登录超星学习通
        
        使用策略模式处理登录逻辑。
        
        Returns:
            bool: 登录是否成功
        """
        try:
            login_url = 'https://passport2.chaoxing.com/'
            self.driver.get(login_url)
            logging.info('打开登录页面')
            
            # 使用工厂创建登录策略
            login_strategy = LoginStrategyFactory.create_strategy(config.use_qr_code)
            if login_strategy.login(self.driver):
                # 获取登录后的Cookies
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