from grader.homework_grader import HomeworkGrader
from config.args import config
import logging


config.api_key = "sk-7xg4nuFTWoLsWNsUbAMnwTclY4pubU9AiJ0DWsXUVubxiAkl"
config.base_url = "https://a1.aizex.me/v1"
config.prepare_model = "gemini-2.5-pro"
config.number_prepare_max = 10
config.number_gen_max = 1
# config.gen_model = "gemini-2.5-pro"
config.gen_model = "gemini-2.5-flash"
# config.max_workers = 1


def main():
    """
    主函数，用于测试重构后的作业批改系统
    """

    # 创建作业批改器实例，直接传入config对象
    grader = HomeworkGrader(config=config)

    # 运行作业批改流程
    logging.info("开始运行作业批改流程...")
    grader.run()
    logging.info("作业批改流程完成")


if __name__ == "__main__":
    main()
