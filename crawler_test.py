from crawler.homework_crawler import ChaoxingHomeworkCrawler
from crawler.webdriver_factory import WebDriverFactoryCreator
from crawler.login_strategies import LoginStrategyFactory
from config import config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# 使用自动管理 ChromeDriver 版本的工厂
WebDriverFactory = WebDriverFactoryCreator().create_factory(headless=False)

LoginStrategy = LoginStrategyFactory.create_strategy(config.use_qr_code)


ChaoxingHomeworkCrawler(WebDriverFactory,
                        LoginStrategy, config).run()
