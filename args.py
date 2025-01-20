import argparse
# revise_homework.py使用
parser = argparse.ArgumentParser()
parser.add_argument('--api_key', type=str, help='API key')
parser.add_argument('--base_url', type=str, help='Base URL',
                    default='https://a1.aizex.me/v1')
parser.add_argument('--max_workers', type=int, default=4, help='改作业的最大线程数')
parser.add_argument('--prepare_model', type=str,
                    default='gpt-4o', help='用来生成分标准和参考分数的大模型')
parser.add_argument('--gen_model', type=str,
                    default='gpt-4o-2024-11-20', help='用来生成单个学生分数的大模型')
parser.add_argument('--number_prepare', type=int,
                    default=10, help='用来生成改分标准和参考分数的学生作业数量')
parser.add_argument('--number_gen', type=int, default=5,
                    help='生成单个学生分数时用来参考的学生-分数对的数量')
parser.add_argument('--class_list_path', type=str,
                    default='homework', help='要改的作业的存放路径')
parser.add_argument('--pulling_students_up', type=bool,
                    default=True, help='是否要捞学生一把')
parser.add_argument('--min_score', type=int, default=60, help='缩放的最高分')
parser.add_argument('--max_score', type=int, default=90, help='缩放的最低分')

# prepare_data.pys使用
parser.add_argument('--course_urls', type=list, help='要爬取的课程的url列表')
parser.add_argument('--class_list', type=list, help='要爬取的课程的班级列表')
parser.add_argument('--chrome_driver_path', type=str, help='ChromeDriver的执行路径')
parser.add_argument('--phonenumber', type=str, help='登录学校通用的手机号')
parser.add_argument('--password', type=str, help='登录学校通用的密码')
parser.add_argument('--max_workers_prepare', type=int,
                    default=6, help='爬作业的最大线程数')


config = parser.parse_args()
