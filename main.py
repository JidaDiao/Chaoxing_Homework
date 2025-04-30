from grader.homework_grader import HomeworkGrader
from config.args import config
import logging
from crawler.homework_crawler import ChaoxingHomeworkCrawler


def main():
    ChaoxingHomeworkCrawler.create(config, headless=False).run()

    # 创建作业批改器实例，直接传入config对象
    grader = HomeworkGrader(config=config)

    # 运行作业批改流程
    logging.info("开始运行作业批改流程...")
    grader.run()
    logging.info("作业批改流程完成")


if __name__ == "__main__":
    main()
