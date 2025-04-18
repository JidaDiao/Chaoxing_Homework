from crawler.homework_crawler import ChaoxingHomeworkCrawler
from revise_homework import HomeworkGrader
from config import config
from utils.my_log import logger as logging

if __name__ == '__main__':
    # 爬取作业
    logging.info("开始爬取作业")
    
    # 使用封装后的静态工厂方法创建爬虫实例
    crawler = ChaoxingHomeworkCrawler.create(config)
    crawler.run()
    
    # 批改作业
    logging.info("开始改作业")
    Grader = HomeworkGrader(config.api_key, config.base_url)
    Grader.run()
