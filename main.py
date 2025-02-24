from prepare_data import HomeworkCrawler
from revise_homework import HomeworkGrader
from config import config
from utils.my_log import logger as logging

if __name__ == '__main__':
    # logging.info("开始爬作业")
    # crawler = HomeworkCrawler(config.chrome_driver_path)
    # crawler.run()
    logging.info("开始改作业")
    Grader = HomeworkGrader(config.api_key, config.base_url)
    Grader.run()
