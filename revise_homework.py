from openai import OpenAI
from utils import *
from concurrent.futures import ThreadPoolExecutor

# 全局变量用于存储学生答案和分数
student_answers_prompt_uncorrected = {}
student_answers_prompt_corrected = {}
student_score_final = {}


def create_messages_with_images(homework_data, student_name):
    """创建包含图片的消息列表"""
    student_answers_list = []
    user_prompt = student_name + '：\n'
    student_answers = homework_data["学生回答"][student_name]
    for a_num, (a_key, a_value) in enumerate(student_answers.items(), 1):
        # 检查文本答案是否为空
        if len(a_value["text"]) == 0:
            user_prompt += a_key + "：" + '' + '\n'
        else:
            user_prompt += a_key + "：" + a_value["text"][0] + '\n'
        # 下载并处理图片
        for img_url in a_value["images"]:
            img_base64 = download_image(img_url)
            if img_base64:
                student_answers_list.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                })

    student_answers_list.append({
        "role": "user",
        "content": user_prompt
    })

    return student_answers_list


def gen_prepare_system_prompt(homework_data, number):
    """生成系统提示信息，包含题目和评分规则"""
    question_stem = "###\n"
    for index, (key, value) in enumerate(homework_data["题目"].items(), start=1):
        question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

    system_prompt = f"""
        你是一名高职计算机教师，上面是你布置的某一次作业中的所有题目和其对应的参考答案（注意，部分题目参考答案可能为空）。：

        {question_stem}

        请根据学生的回答评分，具体要求如下：

        ### 注意事项：
        1. **评分范围：0-100分**，分数尽量不要太工整，保持一定的随机性。
        2. **学生回答形式：** 可能是文本、图片或两者混合，请根据实际情况判断图片与题目内容的对应关系。
        3. **学生水平：** 学生整体水平不高，部分题目可能空白未作答，请结合回答内容和逻辑合理评分。
        4. **分数分布：** 打分尽量使得学生们的分数符合高斯分布。
        5. **主观判断：** 如果对题干存在不理解的部分，需发挥主观能动性，结合学生作答给出适当评分。
        6. **观察阶段：** 前{str(number - 1)}名学生的回答仅作观察，记录题目难易、学生水平等特征来制定打分策略以满足分数分布；从第{str(number)}名开始给出评分。
        7. **整体评分规则：** 观察{str(number)}名学生的作答后，一次性为所有{str(number)}名学生打分，并提供明确的评分标准。
        7. **学会思考：** 如果所有{str(number)}个学生的回答都与题干有一定偏差，是老师与学生在题目外有一些约定没在题干中体现，请发挥主观能动性给予学生分数，而不是将所有学生打低分。

        ### 输出格式：
        1. **观察阶段：** 如果还在前{str(number - 1)}名观察阶段（即前{str(number - 1)}轮），统一回复：`第x轮：pass`，x为对话的轮数
        2. **评分阶段：** 在观察完第{str(number)}名学生作答后（即在第{str(number)}轮）为所有{str(number)}名学生打分，并提供明确的评分标准，按以下格式回复：
        ```
        ### 学生成绩：
        张三：83分  
        李四：64分  
        王五：72分  
        ...  

        ### 本作业评分标准： 
        **...（生成的评分标准）**  
        ```

        请**严格按照**上述格式和规则输出结果，以便后续统一提取学生名字、分数及评分标准信息。
        **不许出现**只有学生姓名没有分数的情况！！！
        **保证出现**{str(number)}名学生的姓名和他们对应的分数！！！
        """
    messages = [{"role": "system", "content": system_prompt}]
    return messages


def gen_few_shot_learning_system_prompt(homework_data, grading_standard):
    question_stem = "###\n"
    for index, (key, value) in enumerate(homework_data["题目"].items(), start=1):
        question_stem += f"{key}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

    system_prompt = f"""
        你是一名高职计算机教师，上面是你布置的某一次作业中的所有题目和其对应的参考答案（注意，部分题目参考答案可能为空）。：

        {question_stem}
        {grading_standard}

        请根据学生的回答评分，具体要求如下：
        ### 注意事项：
        1. 分数取值范围0-100分
        2. 学生的回答可能是文本或图片或混合，所以请自行判断图片属于哪道题
        3. 学生水平不高，有些题目可能空着
        4. 如对题干有不理解的部分发挥主观能动性
        5. 给的分数尽量不要太工整

        ### 规则：
        1. 参考"本作业评分标准"中的评分标准打分
        2. 结合前面所有学生的打分情况进行综合打分

        ### 输出格式：
        1. 只需要输出名字+分数即可，按以下格式回复例如：
        ```
        张三：83分
        ```
        
        请**严格按照**上述格式和规则输出结果，以便后续统一提取学生名字、分数及评分标准信息。
        """
    messages = [{"role": "system", "content": system_prompt}]
    return messages


def prepare_score(client, selected_dict_uncorrected, prepare_system_prompt, number):
    """准备number个参考分数和评分标准"""

    global student_answers_prompt_corrected
    global student_score_final
    context_prompt = context_prepare_prompt(selected_dict_uncorrected, prepare_system_prompt, number)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=context_prompt,
    )
    response_content = response.choices[0].message.content
    print(response_content)
    student_scores, grading_standard = parse_grading_response(response_content)
    for index, (key, value) in enumerate(student_scores.items(), start=1):
        student_score_final[key] = value
    for index, (key, value) in enumerate(selected_dict_uncorrected.items(), start=1):
        try:
            value_ = value
            value_.append({
                "role": "assistant",
                "content": key + "：" + str(student_scores[key]) + "分"
            })
            student_answers_prompt_corrected[key] = value_
        except Exception as e:
            print(e)
    return grading_standard


def gen_score(client, selected_dict_uncorrected, selected_dict_corrected, few_shot_learning_system_prompt):
    """改剩下的"""
    global student_answers_prompt_corrected
    global student_score_final
    context_prompt = context_few_shot_learning_prompt(selected_dict_uncorrected, selected_dict_corrected,
                                                      few_shot_learning_system_prompt)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=context_prompt,
    )
    response_content = response.choices[0].message.content
    print(response_content)
    grades = re.findall(r"(\S+?)：(\d+)分", response_content)
    student_scores = {name: int(score) for name, score in grades}
    for index, (key, value) in enumerate(student_scores.items(), start=1):
        student_score_final[key] = value
    for index, (key, value) in enumerate(selected_dict_uncorrected.items(), start=1):
        try:
            value_ = value
            value_.append({
                "role": "assistant",
                "content": key + "：" + str(student_scores[key]) + "分"
            })
            student_answers_prompt_corrected[key] = value_
        except Exception as e:
            print(e)


def main():
    # 初始化OpenAI客户端
    client = OpenAI(
        api_key="sk-7xg4nuFTWoLsWNsUbAMnwTclY4pubU9AiJ0DWsXUVubxiAkl",
        base_url="https://a1.aizex.me/v1"  # 替换为你的API代理地址
    )

    # 获取要批改的作业目录列表
    class_list = os.listdir('要改的作业')
    homework_dirs = []

    for class_name in class_list:
        homework_name = os.listdir(os.path.join('要改的作业', class_name))
        for homework_name in homework_name:
            homework_dirs.append(os.path.join(os.getcwd(), '要改的作业', class_name, homework_name))

    for homework_dir in homework_dirs:
        # 改变当前工作目录到每个作业的目录
        os.chdir(homework_dir)
        print(f"当前正在改: {os.getcwd()}")
        if os.path.exists('normalized_student_score.json'):
            continue

        # 导入作业数据
        homework_data = import_json_file('./answer.json')

        # 初始化全局变量
        global student_answers_prompt_uncorrected
        global student_score_final
        global student_answers_prompt_corrected

        student_answers_prompt_uncorrected = {}
        student_answers_prompt_corrected = {}
        student_score_final = {}

        # 检查是否存在已保存的学生答案提示词
        if os.path.exists('./student_answers_prompt.json'):
            student_answers_prompt_uncorrected = import_json_file('./student_answers_prompt.json')
        else:
            # 使用线程池并行处理学生回答
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(create_messages_with_images, homework_data, student_name): student_name for
                           student_name in homework_data["学生回答"].keys()}
            for future in futures:
                student_name = futures[future]
                student_answers_prompt_uncorrected[student_name] = future.result()
            with open('student_answers_prompt.json', 'w', encoding='utf-8') as json_file:
                json.dump(student_answers_prompt_uncorrected, json_file, indent=4, sort_keys=True, ensure_ascii=False)

        number = 10

        # 准备number个参考分数和评分标准
        prepare_system_prompt = gen_prepare_system_prompt(homework_data, number)
        selected_dict_uncorrected, selected_keys = randomselect_uncorrected(student_answers_prompt_uncorrected, number)
        grading_standard = prepare_score(client, selected_dict_uncorrected, prepare_system_prompt, number)
        count = 1
        while grading_standard == "" or len(student_score_final) != number:
            student_score_final = {}
            prepare_system_prompt = gen_prepare_system_prompt(homework_data, number)  ###奇怪的bug...可以试试注释掉这段
            selected_dict_uncorrected, selected_keys = randomselect_uncorrected(student_answers_prompt_uncorrected,
                                                                                number)  # 可能是学生选的不好？
            grading_standard = prepare_score(client, selected_dict_uncorrected, prepare_system_prompt, number)
            count += 1
            if count % 2 == 0 and number > 5:
                number -= 1  # 可能是上下文太长了影响模型输出了,少采样几个学生试试。
        pop_uncorrected(student_answers_prompt_uncorrected, selected_keys)
        with open('评分标准.md', 'w', encoding='utf-8') as f:
            f.write(grading_standard)

        # 使用线程池并行评分
        with ThreadPoolExecutor() as executor:
            for index, (key, value) in enumerate(student_answers_prompt_uncorrected.items(), start=1):
                few_shot_learning_system_prompt = gen_few_shot_learning_system_prompt(homework_data,
                                                                                      grading_standard)  ###奇怪的bug...可以试试注释掉这段
                # selected_dict_uncorrected = randompop_uncorrected(student_answers_prompt_uncorrected, 1)
                selected_dict_uncorrected = {key: value}
                selected_dict_corrected = randompop_corrected(student_answers_prompt_corrected, 5)
                executor.submit(gen_score, client, selected_dict_uncorrected, selected_dict_corrected,
                                few_shot_learning_system_prompt)

        print(student_score_final)

        with open('original_student_score.json', 'w', encoding='utf-8') as json_file:
            json.dump(student_score_final, json_file, indent=4, sort_keys=True, ensure_ascii=False)

        # 归一化分数并保存
        normalized_scores = normalize_and_save_grade(student_score_final, min_score=70, max_score=100)

        with open('normalized_student_score.json', 'w', encoding='utf-8') as json_file:
            json.dump(normalized_scores, json_file, indent=4, sort_keys=True, ensure_ascii=False)


if __name__ == "__main__":
    main()
