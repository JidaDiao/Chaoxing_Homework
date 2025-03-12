from crawler.homework_crawler import ChaoxingHomeworkCrawler
from crawler.webdriver_factory import WebDriverFactoryCreator
from crawler.login_strategies import LoginStrategyFactory
from config import config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

config.use_qr_code = False
config.phonenumber = "13958853656"
config.password = "12345ssdlh"
# 使用自动管理 ChromeDriver 版本的工厂
WebDriverFactory = WebDriverFactoryCreator().create_factory(headless=False)

LoginStrategy = LoginStrategyFactory.create_strategy(config.use_qr_code)


ChaoxingHomeworkCrawler(WebDriverFactory,
                        LoginStrategy, config).run()
