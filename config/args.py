import argparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# revise_homework.py使用
parser = argparse.ArgumentParser()
parser.add_argument('--api_key', type=str,
                    default=os.getenv('API_KEY', ''), help='API key')
parser.add_argument('--base_url', type=str,
                    default=os.getenv('BASE_URL', 'https://ollama.jidadiao.fun/v1'), help='Base URL')
parser.add_argument('--max_workers', type=int, default=6, help='改作业的最大线程数')
parser.add_argument('--prepare_model', type=str,
                    default='qwenvl', help='用来生成分标准和参考分数的大模型')
parser.add_argument('--gen_model', type=str,
                    default='qwenvl', help='用来生成单个学生分数的大模型')
parser.add_argument('--number_prepare_max', type=int,
                    default=8, help='用来生成改分标准和参考分数的学生作业数量')
parser.add_argument('--number_prepare_min', type=int,
                    default=3, help='用来生成改分标准和参考分数的学生作业数量')
parser.add_argument('--number_gen_max', type=int, default=3,
                    help='生成单个学生分数时用来参考的学生-分数对的数量')
parser.add_argument('--number_gen_min', type=int, default=1,
                    help='生成单个学生分数时用来参考的学生-分数对的数量')
parser.add_argument('--pulling_students_up', type=bool,
                    default=True, help='是否要捞学生一把')
parser.add_argument('--normalized_min', type=int, default=60, help='缩放的最高分')
parser.add_argument('--normalized_max', type=int, default=85, help='缩放的最低分')
parser.add_argument('--original_min', type=int, default=20, help='低于这个分数不缩放')
parser.add_argument('--original_max', type=int, default=85, help='高于这个分数不缩放')
parser.add_argument('--prepare_system_prompt', type=str, default="""
        ### 角色设定：
        你是一名高职计算机教师，以下是你布置的作业题目及其参考答案（注意，部分题目可能没有参考答案）。：
                    
        请根据学生的回答进行评分，具体要求如下：

        ### 注意事项：
        1. **评分范围：**所有题目分数总和100分，每道题分数尽量均匀分配，分数应客观体现学生的作答情况。
        2. **学生回答形式：** 可能是文本、图片或两者结合，请根据实际情况判断图片与题目内容的对应关系。
        3. **学生水平：** 整体水平较低，部分题目可能空白未作答，请合理结合回答内容和逻辑进行评分，**若无作答则给0分**。
        4. **主观判断：** 若对题干有不理解之处，需结合学生作答进行主观判断，给出适当评分。
        5. **整体评分规则：** 观察完所有{number}名学生的作答后，生成评分标准，并为所有学生打分，同时提供打分依据。
        6. **灵活思考：** 若所有{number}名学生的回答与题干有偏差，可能是题外约定未体现，请灵活给予分数，而非一律低分。
        
        
        ### 输出规则：
        1. **观察阶段：** 观察阶段遵循以下规则：
            - 前{number_}名学生的回答仅作观察，记录题目难度和学生水平等特征，以制定评分策略；从第{number}名开始评分。
            - 若在前{number_}名观察阶段，统一回复：`第x轮：pass`，x为对话轮数。
                    
        2. **评分阶段：** 评分阶段遵循以下规则：
            - 观察完第{number}名学生后，生成评分标准，为打分做参考。
            - 为所有{number}名学生打分，并提供每位学生的打分依据，打分要尽量有理有据。

        3. **评分标准：** 生成的评分标准，要求如下：
            - 评分标准应**客观**，**客观**地反映题目难度和学生水平。
            - 评分标准应**具有可解释性**，能够让学生理解评分依据。
            - 评分标准应**尽量详细！！**，覆盖每道题目的每一个可能的扣分点或得分点。

        ### 输出格式：          
        请**严格按照**以下JSON格式输出评分结果：
                    
        {{
                "student_scores": {{
                        "张三": {{
                                "score": 83,
                                "scoring_criteria": "<根据题目的参考答案和生成的评分标准给出打分依据>"
                        }},
                        "李四": {{
                                "score": 64,
                                "scoring_criteria": "<根据题目的参考答案和生成的评分标准给出打分依据>"
                        }},
                        ...
                }},
                "grading_standard": "<生成的评分标准>"  
        }}

        **确保**所有{number}名学生的姓名和分数以及对应的打分依据都存在！
                    """, help='少样本改作业的系统提示词')

parser.add_argument('--few_shot_learning_system_prompt', type=str, default="""
        ### 角色设定：
        你是一名高职计算机教师，负责评阅学生的作业。以下是你布置的作业题目及其参考答案（注意，部分题目可能没有参考答案）。

        ### 本作业评分标准：
        {grading_standard}

        请根据学生的回答进行评分，具体要求如下：

        ### 注意事项：
        1. **评分范围：0-100分**，分数应有一定随机性，避免过于整齐。
        2. **学生回答形式：** 可能是文本、图片或两者结合，请根据实际情况判断图片与题目内容的对应关系。
        3. **学生水平：** 整体水平较低，部分题目可能空白未作答，请合理结合回答内容和逻辑进行评分，**若无作答则给0分**。
        4. **主观判断：** 若对题干有不理解之处，需结合学生作答进行主观判断，给出适当评分。

        ### 评分规则：
        1. 依据"本作业评分标准"进行评分。
        2. 综合前面所有学生的打分情况以及打分依据进行合理打分。

        ### 输出格式：          
        请**严格按照**以下JSON格式输出评分结果：
        
        {{
                "student_scores": {{
                        "张三": {{
                                "score": 83,
                                "scoring_criteria": "<根据题目的参考答案和生成的评分标准给出打分依据>"
                        }}
                }}
        }}           
        
        **确保**学生的姓名作为键分数以及对应的打分依据都存在！            
        """, help='少样本改作业的系统提示词')
# prepare_data.pys使用
parser.add_argument('--course_urls', type=list, default=[
                    'https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/tch?courseid=249851807&clazzid=116158002&cpi=403105172&enc=864128a6dc492a86849d4623eeccbaeb&t=1741236483060&pageHeader=6&v=2&hideHead=0'], help='要爬取的课程的url列表')
parser.add_argument('--class_list', type=list, default=[],
                    help='要爬取的课程的班级列表，空的话就全爬取')
parser.add_argument('--homework_name_list', type=list, default=[],
                    help='要爬取的作业名列表，空的话就全爬取')
parser.add_argument('--min_ungraded_students', type=int,
                    default=5, help='没批改的学生数超过这个就爬取,-1表示全改完了也爬')
parser.add_argument('--max_workers_prepare', type=int,
                    default=6, help='爬作业的最大线程数')
parser.add_argument('--use_qr_code', type=bool,
                    default=True, help='是否使用二维码登录')
parser.add_argument('--phonenumber', type=str, default=os.getenv('PHONENUMBER', ''), help='登录学校通用的手机号')
parser.add_argument('--password', type=str, default=os.getenv('PASSWORD', ''), help='登录学校通用的密码')

config = parser.parse_args()
