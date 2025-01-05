from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import requests
from bs4 import BeautifulSoup
import re


# 学习通
def chaoxing():
    attackurl = "https://passport2.chaoxing.com/login?fid=&newversion=true&refer=https%3A%2F%2Fi.chaoxing.com"

    # 设置 ChromeOptions
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
    )
    options.headless = True  # 如果调试时需要显示浏览器，则设为 False

    # 设置性能日志捕获
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    options.set_capability('goog:loggingPrefs', caps['goog:loggingPrefs'])

    # 启动 ChromeDriver
    service = Service('C:\Program Files\Google\Chrome\Application\chromedriver.exe')  # 替换为你的 ChromeDriver 路径
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # 打开登录页面
        driver.get(attackurl)

        # 等待页面加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="phone"]'))
        )

        # 输入手机号和密码
        phonenumber = '13958853656'
        password = '12345ssdlh'

        driver.find_element(By.XPATH, '//*[@id="phone"]').send_keys(phonenumber)
        driver.find_element(By.XPATH, '//*[@id="pwd"]').send_keys(password)

        # 点击登录按钮
        driver.find_element(By.XPATH, '//*[@id="loginBtn"]').click()

        # 等待登录完成
        time.sleep(5)

        # 获取登录后的 Cookies
        cookies = driver.get_cookies()
        session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        print("登录成功，获取到的 Cookies")

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Connection': 'keep-alive',
            'Referer': 'https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=237039005&selectClassid=106790350&cpi=403105172&status=-1&v=0&topicid=0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        }

        # 发送 GET 请求
        url = 'https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=237039005&selectClassid=106790350&cpi=403105172&status=-1&v=0&topicid=0'
        response = requests.get(url, headers=headers, cookies=session_cookies)

        # 打印返回的内容
        if response.status_code == 200:
            print("作业列表请求成功!")
            # print(response.text)
        else:
            print(f"请求失败，状态码：{response.status_code}")

        ##############################
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # 定位任务的列表 <li> 元素
        tasks = soup.find_all('li', id=lambda x: x and x.startswith('work'))

        # 存储任务信息的列表
        task_data = []

        # 遍历每个任务项，提取所需信息
        for task in tasks:
            # 提取任务标题
            title = task.find('h2', class_='list_li_tit').text.strip()
            # 提取任务批阅链接
            review_link = task.find('a', class_='piyueBtn')['href']
            # 拼接完整批阅链接
            piyue_url = "https://mooc2-ans.chaoxing.com" + review_link

            # 将提取的数据存入字典
            task_info = {
                'title': title,
                'review_link': piyue_url,
            }

            # 将任务信息添加到列表
            task_data.append(task_info)

        for task in task_data:
            piyue_url = task['review_link']
            title = task['title']
            file_name = title + '.json'
            driver.get(piyue_url)
            time.sleep(3)  # 等待页面加载

            # 监听页面的网络请求
            logs = driver.get_log('performance')
            for log in logs:
                message = log['message']
                if 'mooc2-ans/work/mark-list' in message:  # 过滤目标请求
                    log_json = json.loads(message)['message']['params']
                    if 'request' in log_json and 'url' in log_json['request']:
                        target_url = log_json['request']['url']
                        print(f"捕获的目标批阅列表请求 URL: {target_url}")
                        break

            target_url = re.sub(r'pages=\d+', 'pages={}', target_url)
            student_data = []
            task_list = {}
            for page in range(1, 11):  # 从 1 到 10
                target_url_modified = target_url.format(page)  # 替换 URL 中的 {} 为当前的页码
                response = requests.get(target_url_modified, headers=headers, cookies=session_cookies)

                # 打印返回的内容
                if response.status_code == 200:
                    print("最终批阅链接请求成功!")
                else:
                    print(f"请求失败，状态码：{response.status_code}")

                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # 检查是否有 "暂无数据"
                null_data = soup.find('div', class_='nullData')
                if null_data and "暂无数据" in null_data.text:
                    print("已超出页数，停止爬取。")
                    break
                else:
                    # 查找每个 ul 元素
                    ul_elements = soup.find_all('ul', class_='dataBody_td')

                    # 遍历 ul 元素，提取学生名字和批阅链接
                    for ul in ul_elements:
                        # 提取学生名字
                        name_div = ul.find('div', class_='py_name')
                        if name_div:
                            student_name = name_div.text.strip()
                        else:
                            student_name = "未找到名字"

                        # 提取批阅链接
                        review_link_tag = ul.find('a', class_='cz_py')
                        if review_link_tag:
                            review_link = "https://mooc2-ans.chaoxing.com" + review_link_tag['href']
                        else:
                            review_link = "未找到批阅链接"

                        # 存储学生数据
                        student_data.append({
                            'name': student_name,
                            'review_link': review_link
                        })
            for student in student_data:
                student_name = student['name']
                student_url = student['review_link']
                driver.get(student_url)
                time.sleep(3)  # 等待页面加载

                # 监听页面的网络请求
                logs = driver.get_log('performance')
                for log in logs:
                    message = log['message']
                    if 'https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work' in message:  # 过滤目标请求
                        log_json = json.loads(message)['message']['params']
                        if 'request' in log_json and 'url' in log_json['request']:
                            target_url = log_json['request']['url']
                            print(f"捕获的目标批阅内容请求 URL: {target_url}")
                            break

                response = requests.get(target_url, headers=headers, cookies=session_cookies)
                # 解析 HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # 存储所有题目的数据
                all_questions = []

                # 查找所有题目块
                question_blocks = soup.find_all('div', class_='mark_item1')

                for block in question_blocks:
                    # 提取题目描述
                    question_description_tag = block.find('div', class_='hiddenTitle')
                    if question_description_tag:
                        question_description = question_description_tag.text.strip()
                    else:
                        question_description = "未找到题目描述"

                    # 提取学生答案
                    student_answer_tag = block.find('dl', class_='mark_fill',
                                                    id=lambda x: x and x.startswith('stuanswer_'))
                    if student_answer_tag:
                        # 查找文字答案
                        text_answers = [p.text.strip() for p in student_answer_tag.find_all('p') if p.text.strip()]
                        # 查找图片链接
                        image_answers = [img['src'] for img in student_answer_tag.find_all('img') if
                                         'src' in img.attrs]
                        # 组合学生答案
                        student_answer = {
                            "text": text_answers,
                            "images": image_answers
                        }
                    else:
                        student_answer = {"text": [], "images": []}

                    # 提取正确答案
                    correct_answer_tag = block.find('dl', class_='mark_fill',
                                                    id=lambda x: x and x.startswith('correctanswer_'))
                    if correct_answer_tag:
                        correct_answer = correct_answer_tag.text.strip()
                    else:
                        correct_answer = "未找到正确答案"

                    # 存储题目信息
                    question_data = {
                        "description": question_description,
                        "student_answer": student_answer,
                        "correct_answer": correct_answer
                    }
                    all_questions.append(question_data)
                task_list[student_name] = all_questions
            with open(file_name, 'w', encoding='utf-8') as json_file:
                json.dump(task_list, json_file, indent=4, sort_keys=True, ensure_ascii=False)



    finally:
        # 关闭浏览器
        driver.quit()


# 调用登录函数
if __name__ == "__main__":
    chaoxing()
