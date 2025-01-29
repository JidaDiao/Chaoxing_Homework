from openai import OpenAI
from utils import *
from concurrent.futures import ThreadPoolExecutor
from config.args import config
import logging

# 配置 logging 模块
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class HomeworkGrader:
    """作业批改器类，用于自动批改学生作业

    该类整合了作业批改的所有功能，包括创建消息、生成系统提示、准备评分标准和生成分数等。
    使用OpenAI API进行作业评分，支持图片处理和多线程并行处理。

    Attributes:
        student_answers_prompt_uncorrected (dict): 存储未批改的学生答案
        student_answers_prompt_corrected (dict): 存储已批改的学生答案
        student_score_final (dict): 存储学生最终分数
        client (OpenAI): OpenAI API客户端实例
    """

    def __init__(self, api_key, base_url):
        """初始化作业批改器

        初始化HomeworkGrader类的实例，设置必要的属性和OpenAI客户端。

        Args:
            api_key (str): OpenAI API密钥，用于认证API请求
            base_url (str): OpenAI API基础URL，指定API服务器地址

        Returns:
            None
        """
        self.student_answers_prompt_uncorrected = {}
        self.student_answers_prompt_corrected = {}
        self.student_score_final = {}
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def extract_json_from_response(self, response_content):
        # 使用正则表达式提取JSON字符串
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            # 将JSON字符串解析为字典
            try:
                json_data = json.loads(json_str)
                return json_data
            except json.JSONDecodeError as e:
                logging.error(f"JSON解析错误: {str(e)}")
                return None
        else:
            logging.error("未找到JSON格式内容")
            return None

    def create_messages_with_images(self, homework_data, student_name):
        """创建包含图片的消息列表

        为指定学生创建包含文本答案和图片的消息列表，用于后续的评分。
        将学生的文本答案和图片整合成标准的消息格式。

        Args:
            homework_data (dict): 作业数据，包含学生答案和题目信息
            student_name (str): 学生姓名，用于标识具体学生的答案

        Returns:
            list: 包含学生答案和图片的消息列表，每个元素都是标准的消息格式字典
        """
        student_answers_list = []
        user_prompt = student_name + "：\n"
        student_answers = homework_data["学生回答"][student_name]
        for _, (a_key, a_value) in enumerate(student_answers.items(), 1):
            if len(a_value["text"]) == 0:
                user_prompt += a_key + "：" + "" + "\n"
            else:
                user_prompt += a_key + "：" + a_value["text"][0] + "\n"
            for img_url in a_value["images"]:
                img_base64 = download_image(img_url)
                if img_base64:
                    student_answers_list.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_base64}"
                                    },
                                }
                            ],
                        }
                    )

        student_answers_list.append({"role": "user", "content": user_prompt})
        logging.info(f"正在为学生 {student_name} 创建消息")
        return student_answers_list

    def gen_prepare_system_prompt(self, homework_data, number):
        """生成系统提示信息

        生成包含题目和评分规则的系统提示信息，用于指导模型进行评分。
        将题目信息和评分规则整合成标准的提示格式。

        Args:
            homework_data (dict): 作业数据，包含题目信息和答案
            number (int): 需要处理的题目数量

        Returns:
            list: 包含系统提示信息的消息列表，用于模型评分
        """
        question_stem = "###\n"
        for _, (key, value) in enumerate(homework_data["题目"].items(), start=1):
            question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

        system_prompt = config.prepare_system_prompt.format(
            question_stem=question_stem,
            number=str(number),
            number_=str(number-1)
        )
        messages = [{"role": "system", "content": system_prompt}]
        return messages

    def gen_few_shot_learning_system_prompt(self, homework_data, grading_standard):
        """生成少样本学习系统提示

        生成用于少样本学习的系统提示信息，包含题目信息和评分标准。
        整合题目信息和评分标准，生成引导模型进行少样本学习的提示。

        Args:
            homework_data (dict): 作业数据，包含题目信息和答案
            grading_standard (str): 评分标准，用于指导模型评分

        Returns:
            list: 包含系统提示信息的消息列表，用于模型进行少样本学习
        """
        question_stem = "###\n"
        for _, (key, value) in enumerate(homework_data["题目"].items(), start=1):
            question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

        system_prompt = config.few_shot_learning_system_prompt.format(
            question_stem=question_stem,
            grading_standard=grading_standard
        )

        messages = [{"role": "system", "content": system_prompt}]
        return messages

    def prepare_score(self, selected_dict_uncorrected, prepare_system_prompt, number):
        """准备参考分数和评分标准

        为选定的未批改答案准备参考分数和评分标准。
        使用模型生成评分标准，并对选定的答案进行初步评分。

        Args:
            selected_dict_uncorrected (dict): 选定的未批改答案
            prepare_system_prompt (list): 准备阶段的系统提示
            number (int): 需要处理的答案数量

        Returns:
            str: 生成的评分标准，用于后续批改其他答案
        """
        context_prompt = context_prepare_prompt(
            selected_dict_uncorrected, prepare_system_prompt, number
        )
        response = self.client.chat.completions.create(
            model=config.prepare_model,
            messages=context_prompt,
        )
        response_content = self.extract_json_from_response(
            response.choices[0].message.content)

        logging.info(response_content)
        student_scores = response_content['student_scores']
        grading_standard = response_content['grading_standard']
        for _, (key, value) in enumerate(student_scores.items()):
            self.student_score_final[key] = value['score']
        for _, (key, value) in enumerate(selected_dict_uncorrected.items()):
            try:
                value_ = value
                value_.append(
                    {
                        "role": "assistant",
                        "content": str({key: student_scores[key]}),
                    }
                )
                self.student_answers_prompt_corrected[key] = value_
            except Exception as e:
                logging.error(f"发生错误: {str(e)}")
        logging.info("准备参考分数和评分标准")
        return grading_standard

    def gen_score(self, number_gen, selected_dict_uncorrected, few_shot_learning_system_prompt):
        """生成学生分数

        使用少样本学习方法为未批改的答案生成分数。
        通过参考已批改的样本，为新的答案生成合适的分数。

        Args:
            number_gen (int): 用于参考的样本数量
            selected_dict_uncorrected (dict): 选定的未批改答案
            few_shot_learning_system_prompt (list): 少样本学习系统提示

        Returns:
            None
        """
        selected_dict_corrected = randompop_corrected(
            self.student_answers_prompt_corrected, number_gen
        )
        context_prompt = context_few_shot_learning_prompt(
            selected_dict_uncorrected,
            selected_dict_corrected,
            few_shot_learning_system_prompt,
        )
        response = self.client.chat.completions.create(
            model=config.gen_model,
            messages=context_prompt,
        )
        student_scores = self.extract_json_from_response(
            response.choices[0].message.content)
        logging.info(student_scores)
        count = 1
        while student_scores == {}:
            # 大模型打分出错了，需要重新生成
            selected_dict_corrected = randompop_corrected(
                self.student_answers_prompt_corrected, number_gen
            )  # 换一波学生样本重新打分
            context_prompt = context_few_shot_learning_prompt(
                selected_dict_uncorrected,
                selected_dict_corrected,
                few_shot_learning_system_prompt,
            )
            response = self.client.chat.completions.create(
                model=config.gen_model,
                messages=context_prompt,
            )
            student_scores = self.extract_json_from_response(
                response.choices[0].message.content)
            logging.info(student_scores)
            count += 1
            if count % 2 == 0 and number_gen > config.number_gen_min:
                number_gen -= 1  # 可能是参考样本太多了导致提示词过长了
        for _, (key, value) in enumerate(student_scores.items()):
            self.student_score_final[key] = value['score']
        with open("original_student_score.json", "w", encoding="utf-8") as json_file:
            json.dump(
                self.student_score_final, json_file, indent=4, sort_keys=True, ensure_ascii=False
            )
        for _, (key, value) in enumerate(selected_dict_uncorrected.items()):
            try:
                value_ = value
                value_.append(
                    {
                        "role": "assistant",
                        "content": str({key: student_scores[key]}),
                    }
                )
                self.student_answers_prompt_corrected[key] = value_
            except Exception as e:
                logging.error(f"发生错误: {str(e)}")
        logging.info("开始生成学生分数")

    def normalize_and_save_grades(self, student_scores, normalized_min=60, normalized_max=85, original_min=20, original_max=90):
        """对学生成绩进行归一化处理并保存

        将原始分数进行归一化处理，并将结果保存到当前工作路径下唯一的Excel文件中（学习通导入模版）。
        对于特殊分数区间的成绩进行特殊处理。

        Args:
            student_scores (dict): 包含学生最终成绩的字典
            normalized_min (int, optional): 归一化后的最小分数.
            normalized_max (int, optional): 归一化后的最大分数.
            original_min (int, optional): 原始成绩的最小值. 
            original_max (int, optional): 原始成绩的最大值. 

        Returns:
            dict: 归一化处理后的成绩字典

        Raises:
            ValueError: 当Excel文件中未找到必要的列时抛出
        """
        xls_file = glob.glob("*.xls")[0]
        workbook = xlrd.open_workbook(xls_file, formatting_info=True)
        sheet = workbook.sheet_by_index(0)

        student_name_col_idx = None
        score_col_idx = None

        for col in range(sheet.ncols):
            header = sheet.cell_value(1, col)
            if "学生姓名" in header:
                student_name_col_idx = col
            elif "分数" in header:
                score_col_idx = col

        if student_name_col_idx is None or score_col_idx is None:
            logging.error("未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")
            raise ValueError("未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")

        def scale_score(score):
            # 对于原始分数特别高或者特别低的，直接返回原始分数，中间那些捞一手（基本上缩放后的分数都比原分数高很多）
            if score < original_min or score > original_max:
                return score
            else:
                # 对其他分数进行缩放
                return score / 100 * normalized_max + normalized_min

        normalized_scores = {name: scale_score(
            score) for name, score in student_scores.items()}

        new_workbook = copy(workbook)
        new_sheet = new_workbook.get_sheet(0)

        for row in range(2, sheet.nrows):
            student_name = sheet.cell_value(row, student_name_col_idx)
            if student_name in normalized_scores:
                new_sheet.write(row, score_col_idx,
                                normalized_scores[student_name])

        new_workbook.save(xls_file)
        logging.info("分数更新完成！")
        return normalized_scores

    def _process_homework_directories(self):
        """处理作业目录

        遍历homework目录，获取所有需要批改的作业目录路径。

        Returns:
            list: 作业目录路径列表
        """
        class_list = os.listdir('homework')
        homework_dirs = []

        for class_name in class_list:
            homework_names = os.listdir(os.path.join('homework', class_name))
            for homework_name in homework_names:
                homework_dirs.append(
                    os.path.join(os.getcwd(), 'homework',
                                 class_name, homework_name)
                )
        return homework_dirs

    def _process_student_answers(self, homework_data):
        """处理学生答案

        处理学生答案数据，如果已存在则导入，否则创建新的答案数据。

        Args:
            homework_data (dict): 作业数据

        Returns:
            None
        """
        if os.path.exists("./student_answers_prompt.json"):
            self.student_answers_prompt_uncorrected = import_json_file(
                "./student_answers_prompt.json"
            )
        else:
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(
                        self.create_messages_with_images, homework_data, student_name
                    ): student_name
                    for student_name in homework_data["学生回答"].keys()
                }
            for future in futures:
                student_name = futures[future]
                self.student_answers_prompt_uncorrected[student_name] = future.result(
                )
            with open("student_answers_prompt.json", "w", encoding="utf-8") as json_file:
                json.dump(
                    self.student_answers_prompt_uncorrected,
                    json_file,
                    indent=4,
                    sort_keys=True,
                    ensure_ascii=False,
                )

    def _process_existing_scores(self):
        """处理已存在的分数

        如果存在原始分数文件，则处理已批改和未批改的答案。

        Returns:
            tuple: (grading_standard, bool) 评分标准和是否继续处理的标志
        """
        if os.path.exists("original_student_score.json"):
            self.student_score_final = import_json_file(
                "./original_student_score.json")
            if len(self.student_score_final) >= len(self.student_answers_prompt_uncorrected):
                return None, False

            self.student_answers_prompt_corrected = {
                k: v
                for k, v in self.student_answers_prompt_uncorrected.items()
                if k in self.student_score_final
            }
            for _, (key, value) in enumerate(self.student_answers_prompt_corrected.items()):
                value_ = value
                value_.append({
                    "role": "assistant",
                    "content": key + "：" + str(self.student_score_final[key]) + "分",
                })
                self.student_answers_prompt_corrected[key] = value_

            self.student_answers_prompt_uncorrected = {
                k: v
                for k, v in self.student_answers_prompt_uncorrected.items()
                if k not in self.student_score_final
            }

            with open("./评分标准.md", "r", encoding="utf-8") as f:
                grading_standard = f.read()
            return grading_standard, True

        return None, True

    def _generate_grading_standard(self, homework_data, number_prepare):
        """生成评分标准

        生成新的评分标准，包括准备参考分数和评分规则。

        Args:
            homework_data (dict): 作业数据
            number_prepare (int): 准备的样本数量

        Returns:
            str: 生成的评分标准
        """
        self.student_answers_prompt_corrected = {}
        self.student_score_final = {}

        prepare_system_prompt = self.gen_prepare_system_prompt(
            homework_data, number_prepare)
        selected_dict_uncorrected, selected_keys = randomselect_uncorrected(
            self.student_answers_prompt_uncorrected, number_prepare
        )
        grading_standard = self.prepare_score(
            selected_dict_uncorrected, prepare_system_prompt, number_prepare
        )

        count = 1
        while grading_standard == "" or len(self.student_score_final) != number_prepare:
            self.student_score_final = {}
            prepare_system_prompt = self.gen_prepare_system_prompt(
                homework_data, number_prepare)
            selected_dict_uncorrected, selected_keys = randomselect_uncorrected(
                self.student_answers_prompt_uncorrected, number_prepare
            )
            grading_standard = self.prepare_score(
                selected_dict_uncorrected,
                prepare_system_prompt,
                number_prepare,
            )
            count += 1
            if count % 2 == 0 and number_prepare > config.number_prepare_min:
                number_prepare -= 1

        pop_uncorrected(self.student_answers_prompt_uncorrected, selected_keys)
        with open("评分标准.md", "w", encoding="utf-8") as f:
            f.write(grading_standard)

        return grading_standard

    def _parallel_grading(self, homework_data, grading_standard, number_gen):
        """并行评分处理

        使用线程池并行处理学生答案的评分。

        Args:
            homework_data (dict): 作业数据
            grading_standard (str): 评分标准
            number_gen (int): 生成的样本数量

        Returns:
            None
        """
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            for _, (student_name, student_answer) in enumerate(
                self.student_answers_prompt_uncorrected.items()
            ):
                few_shot_learning_system_prompt = self.gen_few_shot_learning_system_prompt(
                    homework_data, grading_standard
                )
                selected_dict_uncorrected = {student_name: student_answer}
                executor.submit(
                    self.gen_score,
                    number_gen,
                    selected_dict_uncorrected,
                    few_shot_learning_system_prompt,
                )

    def run(self):
        """批改作业的主要流程

        处理作业目录，为每个作业执行完整的批改流程。
        包括导入数据、处理答案、生成评分标准、批改作业和保存结果。

        主要步骤:
        1. 导入作业数据
        2. 处理学生答案
        3. 生成评分标准
        4. 批改作业并生成分数
        5. 保存结果

        Returns:
            None
        """
        homework_dirs = self._process_homework_directories()

        for homework_dir in homework_dirs:
            os.chdir(homework_dir)
            logging.info(f"当前正在改: {os.getcwd()}")

            homework_data = import_json_file("./answer.json")
            self._process_student_answers(homework_data)

            number_prepare = config.number_prepare_max
            number_gen = config.number_gen_max

            grading_standard, should_continue = self._process_existing_scores()
            if not should_continue:
                continue

            if not grading_standard:
                grading_standard = self._generate_grading_standard(
                    homework_data, number_prepare)

            self._parallel_grading(homework_data, grading_standard, number_gen)
            logging.info(self.student_score_final)

            if config.pulling_students_up:
                normalized_scores = self.normalize_and_save_grades(
                    self.student_score_final,
                    normalized_min=config.normalized_min,
                    normalized_max=config.normalized_max,
                    original_min=config.original_min,
                    original_max=config.original_max,
                )

                with open("normalized_student_score.json", "w", encoding="utf-8") as json_file:
                    json.dump(
                        normalized_scores,
                        json_file,
                        indent=4,
                        sort_keys=True,
                        ensure_ascii=False,
                    )
