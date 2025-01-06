import os
import json
from openai import OpenAI
import base64
import requests
from io import BytesIO
from utils import *


def download_image(url):
    """下载图片并转换为base64格式"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Referer': url  # 添加来源页面，部分网站需要
    }
    try:
        # 添加 headers 模拟浏览器请求
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # 使用 BytesIO 处理二进制数据
            image_bytes = BytesIO(response.content).read()
            # 转换为 base64 格式
            return base64.b64encode(image_bytes).decode('utf-8')
        else:
            print(f"请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"下载图片失败: {url}, 错误: {str(e)}")
    return None


def add_messages_with_images(homework_data, student_name, context_message, idx):
    """创建包含图片的消息列表"""
    user_prompt = str(idx) + "号学生-" + student_name + '\n'
    student_answers = homework_data["学生回答"][student_name]
    for a_num, (a_key, a_value) in enumerate(student_answers.items(), 1):
        if len(a_value["text"]) == 0:
            user_prompt += a_key + "：" + '' + '\n'
        else:
            user_prompt += a_key + "：" + a_value["text"][0] + '\n'
        for img_url in a_value["images"]:
            img_base64 = download_image(img_url)
            if img_base64:
                context_message.append({
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

    context_message.append({
        "role": "user",
        "content": user_prompt
    })

    # 处理图片答案

    return context_message


def system_message(homework_data, context_message):
    question_stem = "###\n"
    for index, (key, value) in enumerate(homework_data["题目"].items(), start=1):
        question_stem += f"题目{index}：{value['题干']}\n正确答案：{value['正确答案']}\n###"

    system_prompt = f"""
        你是一名高职计算机教师，上面是你布置的某一次作业中的所有题目和其对应的参考答案（注意，部分题目参考答案可能为空）。：

        {question_stem}

        请根据学生的回答评分。注意事项：
        1. 分数取值范围0-100分
        2. 学生的回答可能是文本或图片或混合，所以请自行判断图片属于哪道题
        3. 学生水平不高，有些题目可能空着
        4. 如对题干有不理解的部分发挥主观能动性
        5. 给的分数尽量不要太工整

        规则：
        1. 输入的前9名学生的分数先不进行打分，观察他们的作答情况，对题目和学生水平有个整体判断
        2. 在观察完第10名学生的作答，根据整体情况一次性给前10名学生的分数进行打分
        3. 10名之后的学生根据之前的情况直接打分

        输出格式：
        1. 只需要输出名字+分数即可，例如：张三：83分
        2. 还不需要评分时回复：pass
        """
    messages = {"role": "system", "content": system_prompt}
    context_message.append(messages)
    return context_message


def grade_homework(client, homework_data, student_name, context_message, idx):
    """循环评分学生的作业"""

    context_message = add_messages_with_images(homework_data, student_name, context_message, idx)

    if idx >= 10:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=context_message,
            )

            print("第" + str(idx) + "轮:" + response.choices[0].message.content)

        except Exception as e:
            print(f"评分出错: {str(e)}")

        return response.choices[0].message.content
    else:
        print("第" + str(idx) + "轮: pass")
        return "pass"


def main():
    client = OpenAI(
        api_key="sk-RLQ1QiZSGs9TWcZDqtHw3aBVO1zWU7GkisyO7I9zWA8Ip0Zf",
        base_url="https://a1.aizex.me/v1"  # 替换为你的API代理地址
    )

    # 导入作业数据
    homework_data = import_json_file('./任务：DHCP服务器搭建.json')
    context_message = []
    context_message = system_message(homework_data, context_message)
    idx = 1

    # 评分所有学生的作业
    for student_name in homework_data["学生回答"].keys():
        assistant_answer = grade_homework(client, homework_data, student_name, context_message, idx)
        context_message.append({
            "role": "assistant",
            "content": assistant_answer
        })
        idx += 1


if __name__ == "__main__":
    main()
