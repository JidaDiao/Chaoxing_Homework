from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

from .client import CrawlerClient


class HomeworkProcessor:
    """Fetch and format homework answers for all students."""

    def __init__(self, context: BrowserContext, max_concurrent: int = 10) -> None:
        self.context = context
        self.max_concurrent = max_concurrent

    async def get_all_students_data(self, grading_url: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all students' answers for a homework grading URL."""
        students = await self._get_student_list(grading_url)
        if not students:
            return {}

        logging.info("Student list fetched: %s", len(students))

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def fetch_with_limit(student: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
            async with semaphore:
                return await self._get_student_answers(student)

        results = await asyncio.gather(
            *[fetch_with_limit(student) for student in students],
            return_exceptions=True,
        )

        student_data: Dict[str, List[Dict[str, Any]]] = {}
        for idx, result in enumerate(results):
            student_name = students[idx]["name"]
            if isinstance(result, Exception):
                logging.error("Failed to fetch student data for index %s: %s", idx + 1, result)
            elif result:
                student_data[student_name] = result
        logging.info("Student data collected: %s", len(student_data))
        return student_data

    async def _get_student_list(self, grading_url: str) -> List[Dict[str, str]]:
        students: List[Dict[str, str]] = []
        page = await self.context.new_page()
        client = CrawlerClient(page)
        try:
            await client.setup_response_capture(["mooc2-ans/work/mark-list"])
            await client.goto(grading_url)
            await page.wait_for_timeout(2000)

            mark_list_url = client.get_captured_url("mooc2-ans/work/mark-list")
            if not mark_list_url:
                logging.error("Failed to capture student list URL")
                return students

            page_num = 1
            paginated_url = mark_list_url.replace("pages=1", "pages={}")
            while True:
                url = paginated_url.format(page_num)
                html = await client.fetch_html(url)
                page_students = self._parse_student_list(html)
                if not page_students:
                    break
                students.extend(page_students)
                page_num += 1
        finally:
            await page.close()
        return students

    def _parse_student_list(self, html: str) -> List[Dict[str, str]]:
        students: List[Dict[str, str]] = []
        soup = BeautifulSoup(html, "html.parser")

        null_data = soup.find("div", class_="nullData")
        if null_data and "暂无数据" in null_data.text:
            return students

        for ul in soup.find_all("ul", class_="dataBody_td"):
            name_div = ul.find("div", class_="py_name")
            if not name_div:
                continue
            name = name_div.text.strip()
            review_a = ul.find("a", class_="cz_py")
            if not review_a or "data" not in review_a.attrs:
                continue
            review_url = "https://mooc2-ans.chaoxing.com" + review_a["data"].replace("&amp;", "&")
            students.append({"name": name, "review_url": review_url})
        return students

    async def _get_student_answers(self, student: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        review_url = student["review_url"]
        page = await self.context.new_page()
        client = CrawlerClient(page)
        try:
            await client.setup_response_capture(["review-work"])
            await client.goto(review_url)
            await page.wait_for_timeout(2000)

            content_url = client.get_captured_url("review-work")
            if not content_url:
                logging.warning("Failed to capture review content URL")
                return None

            html = await client.fetch_html(content_url)
            return self._parse_student_answers(html)
        finally:
            await page.close()

    def _parse_student_answers(self, html: str) -> List[Dict[str, Any]]:
        answers: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html, "html.parser")
        for block in soup.find_all("div", class_="mark_item1"):
            desc_div = block.find("div", class_="hiddenTitle")
            description = self._extract_content(desc_div)

            answer_dl = block.find(
                "dl",
                class_="mark_fill",
                id=lambda x: x and x.startswith("stuanswer_"),
            )
            student_answer = self._extract_content(answer_dl)

            correct_dl = block.find(
                "dl",
                class_="mark_fill",
                id=lambda x: x and x.startswith("correctanswer_"),
            )
            correct_answer = (
                correct_dl.text.strip().replace("参考答案：", "", 1) if correct_dl else "此题无参考答案"
            )
            answers.append(
                {
                    "description": description,
                    "student_answer": student_answer,
                    "correct_answer": correct_answer,
                }
            )
        return answers

    def _extract_content(self, element: Any) -> Dict[str, List[str]]:
        if not element:
            return {"text": [], "images": []}

        text_contents: List[str] = []
        for p in element.find_all("p"):
            html_content = str(p).replace("<br>", "\n").replace("<br/>", "\n")
            text = BeautifulSoup(html_content, "html.parser").get_text().strip()
            if text:
                text_contents.append(text)

        combined_text = ["\n".join(text_contents)] if text_contents else []
        images = [img["src"] for img in element.find_all("img") if "src" in img.attrs]
        return {"text": combined_text, "images": images}

    def format_results(self, student_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Format student answers into the grader-compatible schema."""
        result: Dict[str, Any] = {"题目": {}, "学生回答": {}}
        if not student_data:
            return result

        student_names = list(student_data.keys())
        if not student_names:
            return result

        for student_name in student_names:
            result["学生回答"][student_name] = {}

        first_student = student_names[0]
        questions = student_data[first_student]

        for index, question in enumerate(questions, 1):
            key = f"题目{index}"
            result["题目"][key] = {
                "题干": question["description"],
                "正确答案": question["correct_answer"],
            }
            for student_name in student_names:
                answers = student_data.get(student_name, [])
                if index - 1 < len(answers):
                    result["学生回答"][student_name][key] = answers[index - 1]["student_answer"]
        return result
