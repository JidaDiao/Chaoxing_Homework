from crawler.homework_crawler import ChaoxingHomeworkCrawler
from config import config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# 配置测试参数
config.use_qr_code = False
config.phonenumber = "13"
config.password = "1"
config.homework_name_list = ['']
config.course_urls = [
    'https://mooc2-ans.chaoxing.com/mooc2-an']

# 使用静态工厂方法创建爬虫实例并运行
# headless参数设置为False，表示使用有GUI界面的浏览器
ChaoxingHomeworkCrawler.create(config, headless=False).run()
