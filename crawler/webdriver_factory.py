from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from .interface import WebDriverFactory
import os


class BaseWebDriverFactory(WebDriverFactory):
    """WebDriver工厂基类
    
    为Chrome WebDriver工厂提供基础配置和功能。
    """
    
    def _configure_options(self, headless: bool = False, download_dir: str = None) -> ChromeOptions:
        """配置Chrome选项
        
        Args:
            headless: 是否使用无头模式
            download_dir: 下载文件保存的目录路径，如果为None则使用默认的downloads目录
            
        Returns:
            ChromeOptions: 配置好的Chrome选项
        """
        options = ChromeOptions()
        # 禁用自动控制特性检测
        options.add_argument('--disable-blink-features=AutomationControlled')
        # 设置用户代理
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
        )
        # 配置无头模式
        options.headless = headless
        
        # 配置性能日志捕获
        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        options.set_capability('goog:loggingPrefs', caps['goog:loggingPrefs'])
        
        # 设置下载目录
        if download_dir is None:
            download_dir = os.path.join(os.getcwd(), "downloads")
        
        # 确保下载目录存在
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        # 配置下载选项
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
    
    def create_driver(self) -> webdriver.Chrome:
        """创建WebDriver实例（由子类实现具体逻辑）"""
        pass


class HeadlessWebDriverFactory(BaseWebDriverFactory):
    """无头模式WebDriver工厂类
    
    创建无头模式的Chrome WebDriver实例，用于后台运行而不显示浏览器窗口。
    """

    def create_driver(self, download_dir: str = None) -> webdriver.Chrome:
        """创建无头模式的Chrome WebDriver实例
        
        Args:
            download_dir: 下载文件保存的目录路径，如果为None则使用默认的downloads目录
            
        Returns:
            webdriver.Chrome: 配置好的Chrome WebDriver实例
        """
        options = self._configure_options(headless=True, download_dir=download_dir)
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)


class NormalWebDriverFactory(BaseWebDriverFactory):
    """普通模式WebDriver工厂类
    
    创建普通模式的Chrome WebDriver实例，可视化显示浏览器窗口。
    """

    def create_driver(self, download_dir: str = None) -> webdriver.Chrome:
        """创建普通模式的Chrome WebDriver实例
        
        Args:
            download_dir: 下载文件保存的目录路径，如果为None则使用默认的downloads目录
            
        Returns:
            webdriver.Chrome: 配置好的Chrome WebDriver实例
        """
        options = self._configure_options(headless=False, download_dir=download_dir)
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)


class WebDriverFactoryCreator:
    """WebDriver工厂创建器
    
    根据需要创建不同类型的WebDriver工厂实例。
    """
    
    @staticmethod
    def create_factory(headless: bool = True) -> WebDriverFactory:
        """创建WebDriver工厂
        
        Args:
            headless: 是否创建无头模式的WebDriver工厂
            
        Returns:
            WebDriverFactory: WebDriver工厂实例
        """
        return HeadlessWebDriverFactory() if headless else NormalWebDriverFactory()
