from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import re
import requests
from bs4 import BeautifulSoup


# 登录学习通
def login_learningspace():
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
        url = 'https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work?courseid=245486443&clazzid=104412878&workId=37841094&workAnswerId=53036225&groupId=0&from=&sort=0&order=0&status=0&pages=1&size=20&topicid=0'
        response = requests.get(url, headers=headers, cookies=session_cookies)
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
            student_answer_tag = block.find('dl', class_='mark_fill', id=lambda x: x and x.startswith('stuanswer_'))
            if student_answer_tag:
                # 查找文字答案
                text_answers = [p.text.strip() for p in student_answer_tag.find_all('p') if p.text.strip()]
                # 查找图片链接
                image_answers = [img['src'] for img in student_answer_tag.find_all('img') if 'src' in img.attrs]
                # 组合学生答案
                student_answer = {
                    "text": text_answers,
                    "images": image_answers
                }
            else:
                student_answer = {"text": [], "images": []}

            # 提取正确答案
            correct_answer_tag = block.find('dl', class_='mark_fill', id=lambda x: x and x.startswith('correctanswer_'))
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

        # 打印提取的数据
        for i, question in enumerate(all_questions, 1):
            print(f"题目 {i}:")
            print(f"描述: {question['description']}")
            print("学生答案:")
            print(f"  文字: {question['student_answer']['text']}")
            print(f"  图片: {question['student_answer']['images']}")
            print(f"正确答案: {question['correct_answer']}")
            print("-" * 50)
    finally:
        # 关闭浏览器
        driver.quit()


if __name__ == "__main__":
    login_learningspace()
