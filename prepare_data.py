import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading
import os
from utils import *
from args import config
import logging

# 配置logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def process_student(
        student, headers, session_cookies, driver_queue, task_list_lock, task_list
):
    # 从队列中获取driver
    driver = driver_queue.get()
    try:
        student_name = student["name"]
        student_url = student["review_link"]
        driver.get(student_url)
        time.sleep(2)  # 等待页面加载

        # 获取浏览器性能日志
        logs = driver.get_log("performance")
        target_url = None
        for log in logs:
            message = log["message"]
            if (
                    "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
                    in message
            ):
                log_json = json.loads(message)["message"]["params"]
                if "request" in log_json and "url" in log_json["request"]:
                    target_url = log_json["request"]["url"]
                    break

        if target_url:
            response = requests.get(
                target_url, headers=headers, cookies=session_cookies)
            soup = BeautifulSoup(response.content, "html.parser")
            all_questions = []
            question_blocks = soup.find_all("div", class_="mark_item1")

            for block in question_blocks:
                # 提取题目描述
                question_description_tag = block.find(
                    "div", class_="hiddenTitle")
                if question_description_tag:
                    question_description = question_description_tag.text.strip()
                else:
                    question_description = "未找到题目描述"

                # 提取学生答案
                student_answer_tag = block.find(
                    "dl",
                    class_="mark_fill",
                    id=lambda x: x and x.startswith("stuanswer_"),
                )
                if student_answer_tag:
                    # 查找文字答案
                    text_answers = [
                        p.text.strip()
                        for p in student_answer_tag.find_all("p")
                        if p.text.strip()
                    ]
                    # 查找图片链接
                    image_answers = [
                        img["src"]
                        for img in student_answer_tag.find_all("img")
                        if "src" in img.attrs
                    ]
                    # 组合学生答案
                    student_answer = {"text": text_answers,
                                      "images": image_answers}
                else:
                    student_answer = {"text": [], "images": []}

                # 提取正确答案
                correct_answer_tag = block.find(
                    "dl",
                    class_="mark_fill",
                    id=lambda x: x and x.startswith("correctanswer_"),
                )
                if correct_answer_tag:
                    correct_answer = correct_answer_tag.text.strip()
                else:
                    correct_answer = "未找到正确答案"

                # 存储题目信息
                question_data = {
                    "description": question_description,
                    "student_answer": student_answer,
                    "correct_answer": correct_answer.replace("正确答案：", "", 1),
                }
                all_questions.append(question_data)

            # 使用锁来保护共享资源
            with task_list_lock:
                task_list[student_name] = all_questions
    finally:
        # 将driver放回队列
        driver_queue.put(driver)


# 学习通
# 登录并获取作业信息
# 主要流程包括：登录、获取课程链接、解析作业列表、下载作业数据
# 使用多线程提高效率


def chaoxing():
    loginurl = "https://passport2.chaoxing.com/login?fid=&newversion=true&refer=https%3A%2F%2Fi.chaoxing.com"

    # 设置 ChromeOptions
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
    )
    options.headless = True  # 如果调试时需要显示浏览器，则设为 False

    # 设置性能日志捕获
    caps = DesiredCapabilities.CHROME
    caps["goog:loggingPrefs"] = {"performance": "ALL"}
    options.set_capability("goog:loggingPrefs", caps["goog:loggingPrefs"])
    class_list = config.class_list
    course_urls = config.course_urls

    # 启动 ChromeDriver
    service = Service(config.chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # 打开登录页面
        driver.get(loginurl)
        logging.info('打开登录页面')

        # 等待页面加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="phone"]'))
        )

        # 输入手机号和密码
        phonenumber = config.phonenumber
        password = config.password

        driver.find_element(
            By.XPATH, '//*[@id="phone"]').send_keys(phonenumber)
        driver.find_element(By.XPATH, '//*[@id="pwd"]').send_keys(password)

        # 点击登录按钮
        driver.find_element(By.XPATH, '//*[@id="loginBtn"]').click()

        # 等待登录完成
        time.sleep(3)

        # 获取登录后的 Cookies
        cookies = driver.get_cookies()
        session_cookies = {cookie['name']: cookie['value']
                           for cookie in cookies}
        logging.info('登录成功，获取到的 Cookies')

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Connection": "keep-alive",
            "Referer": "https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=237039005&selectClassid=106790350&cpi=403105172&status=-1&v=0&topicid=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        }
        driver_queue = Queue()

        for course_url in course_urls:
            # 打开目标网页
            driver.get(course_url)
            time.sleep(3)  # 等待页面加载
            # 监听页面的网络请求
            logs = driver.get_log("performance")
            for log in logs:
                message = log["message"]
                if "mooc2-ans/work/list" in message:  # 过滤目标请求
                    log_json = json.loads(message)["message"]["params"]
                    if "request" in log_json and "url" in log_json["request"]:
                        list_url = log_json["request"]["url"]
                        logging.info(f"捕获的作业列表请求 URL: {list_url}")
                        break

            page_num = 1
            # 存储任务信息的列表
            task_data = []
            stop_flag = False
            while True:
                if stop_flag:
                    break
                url = convert_url(list_url, page_num)
                response = requests.get(
                    url, headers=headers, cookies=session_cookies)

                # 打印返回的内容
                if response.status_code == 200:
                    logging.info("作业列表请求成功!")
                else:
                    logging.error(f"请求失败，状态码：{response.status_code}")
                    break
                page_num += 1

                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(response.content, "html.parser")

                # 定位任务的列表 <li> 元素
                tasks = soup.find_all(
                    "li", id=lambda x: x and x.startswith("work"))

                # 遍历每个任务项，提取所需信息
                for task in tasks:
                    # 班级
                    class_name = (
                        task.find("div", class_="list_class").get(
                            "title", "").strip()
                    )
                    if class_name not in class_list:
                        continue
                    # 提取任务标题
                    title = task.find("h2", class_="list_li_tit").text.strip()
                    # 作答时间
                    answer_time = (task.find("p", class_="list_li_time").find(
                        "span").text.strip())
                    # 待批人数
                    pending_review = int(
                        task.find("em", class_="fs28").text.strip())
                    # 提取任务批阅链接
                    review_link = task.find("a", class_="piyueBtn")["href"]
                    # 拼接完整批阅链接
                    piyue_url = "https://mooc2-ans.chaoxing.com" + review_link
                    # 大于5个学生要改才自动改
                    if pending_review > 5:
                        # 将提取的数据存入字典
                        task_info = {
                            "班级": class_name,
                            "作答时间": answer_time,
                            "作业名": title,
                            "review_link": piyue_url,
                        }
                        task_exists = any(
                            t for t in task_data
                            if t["班级"] == task_info["班级"]
                            and t["作答时间"] == task_info["作答时间"]
                            and t["作业名"] == task_info["作业名"]
                        )
                        if task_exists:
                            logging.info("作业已存在，跳过")
                            stop_flag = True
                            break
                        else:
                            # 将任务信息添加到列表
                            task_data.append(task_info)

            for task in task_data:
                save_path = (
                    "homework/"
                    + sanitize_folder_name(task["班级"])
                    + "/"
                    + sanitize_folder_name(task["作业名"] + task["作答时间"])
                )
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                else:
                    continue
                piyue_url = task["review_link"]
                file_name = "answer.json"
                print("当前批阅链接：" + piyue_url)
                download(driver, save_path, piyue_url)
                driver.get(piyue_url)
                time.sleep(2)  # 等待页面加载

                # 监听页面的网络请求
                logs = driver.get_log("performance")
                for log in logs:
                    message = log["message"]
                    if "mooc2-ans/work/mark-list" in message:  # 过滤目标请求
                        log_json = json.loads(message)["message"]["params"]
                        if "request" in log_json and "url" in log_json["request"]:
                            target_url = log_json["request"]["url"]
                            print(f"捕获的目标批阅列表请求 URL: {target_url}")
                            break

                target_url = re.sub(r"pages=\d+", "pages={}", target_url)
                student_data = []
                task_list = {}
                final_page_num = 1
                while True:
                    target_url_modified = target_url.format(
                        final_page_num
                    )  # 替换 URL 中的 {} 为当前的页码
                    response = requests.get(
                        target_url_modified,
                        headers=headers,
                        cookies=session_cookies,
                    )

                    # 打印返回的内容
                    if response.status_code == 200:
                        logging.info("最终批阅链接请求成功!")
                    else:
                        logging.error(f"请求失败，状态码：{response.status_code}")

                    # 使用 BeautifulSoup 解析 HTML
                    soup = BeautifulSoup(response.content, "html.parser")

                    # 检查是否有 "暂无数据"
                    null_data = soup.find("div", class_="nullData")
                    if null_data and "暂无数据" in null_data.text:
                        logging.info("已超出页数，停止爬取。")
                        break
                    else:
                        final_page_num += 1
                        # 查找每个 ul 元素
                        ul_elements = soup.find_all(
                            "ul", class_="dataBody_td")

                        # 遍历 ul 元素，提取学生名字和批阅链接
                        for ul in ul_elements:
                            # 提取学生名字
                            name_div = ul.find("div", class_="py_name")
                            if name_div:
                                student_name = name_div.text.strip()
                            else:
                                student_name = "未找到名字"

                            # 提取批阅链接
                            review_link_tag = ul.find("a", class_="cz_py")
                            if review_link_tag:
                                review_link = (
                                    "https://mooc2-ans.chaoxing.com"
                                    + review_link_tag["href"]
                                )
                            else:
                                review_link = "未找到批阅链接"

                            # 存储学生数据
                            student_data.append(
                                {"name": student_name,
                                    "review_link": review_link}
                            )
                    # 创建多个WebDriver实例
                    num_threads = config.max_workers_prepare  # 可以根据需要调整线程数
                    if driver_queue.empty():
                        for _ in range(num_threads):
                            options = webdriver.ChromeOptions()
                            # 设置ChromeOptions...
                            driver_ = webdriver.Chrome(
                                service=service, options=options)
                            driver_queue.put(driver_)

                    # 创建线程锁
                    task_list_lock = threading.Lock()

                    # 使用线程池处理学生数据
                    with ThreadPoolExecutor(max_workers=num_threads) as executor:
                        futures = []
                        for student in student_data:
                            future = executor.submit(
                                process_student,
                                student,
                                headers,
                                session_cookies,
                                driver_queue,
                                task_list_lock,
                                task_list,
                            )
                            futures.append(future)

                        # 等待所有任务完成
                        for future in futures:
                            future.result()

                    final_list = {}
                    final_list["题目"] = {}
                    final_list["学生回答"] = {}
                    student_name_list = list(task_list.keys())
                    len_task = len(task_list[student_name_list[0]])
                    len_student = len(student_name_list)
                    for j in range(len_student):
                        final_list["学生回答"][student_name_list[j]] = {}
                    for i in range(len_task):
                        final_list["题目"]["题目" + str(i + 1)] = {}
                        final_list["题目"]["题目" + str(i + 1)]["题干"] = task_list[
                            student_name_list[0]
                        ][i]["description"]
                        final_list["题目"]["题目" + str(i + 1)]["正确答案"] = task_list[
                            student_name_list[0]
                        ][i]["correct_answer"]
                        for j in range(len_student):
                            final_list["学生回答"][student_name_list[j]][
                                "题目" + str(i + 1)
                            ] = task_list[student_name_list[j]][i]["student_answer"]
                    with open(
                            os.path.join(save_path, file_name), "w", encoding="utf-8"
                    ) as json_file:
                        json.dump(
                            final_list,
                            json_file,
                            indent=4,
                            sort_keys=True,
                            ensure_ascii=False,
                        )
        logging.info("down")

    finally:
        # 关闭浏览器
        driver.quit()


# 调用登录函数
if __name__ == "__main__":
    chaoxing()
