from crawler.homework_crawler import ChaoxingHomeworkCrawler
from config import config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# 配置测试参数
config.use_qr_code = False
config.phonenumber = "13958853656"
config.password = "12345ssdlh"
config.homework_name_list = ['自定义结构元']
config.course_urls = [
    'https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/tch?courseid=249745947&clazzid=115077084&cpi=403105172&enc=ee75bfaba53a455ba1c214e4a8c1d67a&t=1743516023844&pageHeader=6&v=2&hideHead=0']

# 使用静态工厂方法创建爬虫实例并运行
# headless参数设置为False，表示使用有GUI界面的浏览器
ChaoxingHomeworkCrawler.create(config, headless=False).run()
