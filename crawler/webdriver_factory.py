from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from .interface import WebDriverFactory
import os


class HeadlessWebDriverFactory(WebDriverFactory):
    """无头模式WebDriver工厂类

    创建无头模式的Chrome WebDriver实例。
    """

    def create_driver(self) -> webdriver.Chrome:
        options = ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
        )
        options.headless = True

        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        options.set_capability('goog:loggingPrefs', caps['goog:loggingPrefs'])

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)


class NormalWebDriverFactory(WebDriverFactory):
    """普通模式WebDriver工厂类

    创建普通模式的Chrome WebDriver实例。
    """

    def create_driver(self) -> webdriver.Chrome:
        options = ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
        )
        caps = DesiredCapabilities.CHROME
        caps["goog:loggingPrefs"] = {"performance": "ALL"}
        options.set_capability("goog:loggingPrefs", caps["goog:loggingPrefs"])

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
