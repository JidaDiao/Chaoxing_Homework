import argparse
import asyncio
import logging

from config._args import config
from crawler.crawler import ChaoxingCrawler
from grader.homework_grader import HomeworkGrader


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def run_crawler() -> list:
    crawler = ChaoxingCrawler(config)
    return await crawler.run()


def run_grader() -> None:
    grader = HomeworkGrader(config=config)
    logging.info("Starting grading flow...")
    grader.run()
    logging.info("Grading flow finished")


async def main() -> None:
    parser = argparse.ArgumentParser(description="超星作业自动批改系统")
    parser.add_argument(
        "--mode",
        choices=["crawl", "grade", "all"],
        default="all",
        help="运行模式: crawl=仅爬取, grade=仅批改, all=全部",
    )
    args = parser.parse_args()

    if args.mode in ["crawl", "all"]:
        logging.info("Starting crawl flow...")
        saved_dirs = await run_crawler()
        logging.info("Crawl finished, saved %s homework folders", len(saved_dirs))

    if args.mode in ["grade", "all"]:
        run_grader()


if __name__ == "__main__":
    asyncio.run(main())
