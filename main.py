from prepare_data import HomeworkCrawler
from config import config
if __name__ == '__main__':
    crawler = HomeworkCrawler(config.chrome_driver_path)
    crawler.run()