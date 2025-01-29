from prepare_data import HomeworkCrawler
from revise_homework import HomeworkGrader
from config import config
import logging

# 配置logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
if __name__ == '__main__':
    # logging.info("开始爬作业")
    # crawler = HomeworkCrawler(config.chrome_driver_path)
    # crawler.run()
    logging.info("开始改作业")
    Grader = HomeworkGrader(config.api_key, config.base_url)
    Grader.run()
