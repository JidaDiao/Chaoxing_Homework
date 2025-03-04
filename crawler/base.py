from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import ChromeOptions
from typing import Dict, Any, Optional

class LoginStrategy(ABC):
    """登录策略抽象类
    
    定义了不同登录方式的接口，支持账号密码登录和二维码登录等多种方式。
    """
    @abstractmethod
    def login(self, driver: webdriver.Chrome) -> bool:
        """执行登录操作
        
        Args:
            driver: Chrome WebDriver实例
            
        Returns:
            bool: 登录是否成功
        """
        pass

class DataProcessor(ABC):
    """数据处理策略抽象类
    
    定义了不同数据处理方式的接口，支持作业数据、学生答案等多种数据的处理。
    """
    @abstractmethod
    def process(self, data: Any) -> Dict:
        """处理数据
        
        Args:
            data: 待处理的数据
            
        Returns:
            Dict: 处理后的数据
        """
        pass

class WebDriverBuilder:
    """WebDriver构建器类
    
    使用建造者模式构建WebDriver实例，支持灵活配置各种选项。
    """
    def __init__(self):
        self.options = ChromeOptions()
        self.download_dir = None
        self.headless = True

    def set_user_agent(self, user_agent: str) -> 'WebDriverBuilder':
        """设置User-Agent
        
        Args:
            user_agent: User-Agent字符串
        """
        self.options.add_argument(f'user-agent={user_agent}')
        return self

    def set_download_dir(self, download_dir: str) -> 'WebDriverBuilder':
        """设置下载目录
        
        Args:
            download_dir: 下载目录路径
        """
        self.download_dir = download_dir
        return self

    def set_headless(self, headless: bool) -> 'WebDriverBuilder':
        """设置是否使用无头模式
        
        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        return self

    def build(self, chrome_driver_path: str) -> webdriver.Chrome:
        """构建WebDriver实例
        
        Args:
            chrome_driver_path: ChromeDriver路径
            
        Returns:
            webdriver.Chrome: 配置好的WebDriver实例
        """
        self.options.headless = self.headless
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        
        if self.download_dir:
            prefs = {
                'download.default_directory': self.download_dir,
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True
            }
            self.options.add_experimental_option('prefs', prefs)
        
        service = Service(chrome_driver_path)
        return webdriver.Chrome(service=service, options=self.options)