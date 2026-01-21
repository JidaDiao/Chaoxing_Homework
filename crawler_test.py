import asyncio
import logging

from config._args import config
from crawler.crawler import ChaoxingCrawler


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 配置测试参数（请在 .env 文件中设置真实的 PHONENUMBER 和 PASSWORD）
config.use_qr_code = False
config.phonenumber = "13"  # 测试占位符，生产请使用 .env
config.password = "1"  # 测试占位符，生产请使用 .env
config.homework_name_list = [""]
config.course_urls = ["https://mooc2-ans.chaoxing.com/mooc2-an"]


async def main() -> None:
    crawler = ChaoxingCrawler(config)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
