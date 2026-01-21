from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from core.browser import BrowserManager
from utils.tools import convert_url, sanitize_folder_name

from .auth import LoginStrategy, create_login_strategy
from .client import CrawlerClient
from .processor import HomeworkProcessor


class ChaoxingCrawler:
    """Playwright-based async crawler for Chaoxing homework data."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.browser_manager: Optional[BrowserManager] = None
        self.login_strategy: LoginStrategy = create_login_strategy(config)
        self.cookies: List[Dict] = []

    async def run(self) -> List[Path]:
        """Run the full crawl workflow."""
        saved_dirs: List[Path] = []
        download_dir = self._init_download_dir()
        max_workers = self._resolve_max_workers()

        async with BrowserManager(
            headless=getattr(self.config, "headless", False),
            max_contexts=max_workers,
            download_path=download_dir,
        ) as browser:
            self.browser_manager = browser

            if not await self._login():
                logging.error("Login failed; aborting crawler")
                return saved_dirs

            tasks = await self._get_all_homework_tasks()
            if not tasks:
                logging.warning("No homework tasks found")
                return saved_dirs

            semaphore = asyncio.Semaphore(max_workers)

            async def process_with_limit(task: Dict[str, Any]) -> Optional[Path]:
                async with semaphore:
                    return await self._process_homework(task, max_workers)

            results = await asyncio.gather(
                *[process_with_limit(task) for task in tasks],
                return_exceptions=True,
            )

            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logging.error("Failed to process homework #%s: %s", idx + 1, result)
                elif result:
                    saved_dirs.append(result)

        logging.info("Crawl finished: %s/%s", len(saved_dirs), len(tasks))
        return saved_dirs

    def _resolve_max_workers(self) -> int:
        configured = getattr(self.config, "max_workers_prepare", 0) or 0
        return max(int(configured), 10)

    def _init_download_dir(self) -> str:
        download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(download_dir, exist_ok=True)
        return download_dir

    async def _login(self) -> bool:
        """Perform login and capture shared cookies."""
        if not self.browser_manager:
            raise RuntimeError("Browser manager is not initialized")
        login_url = "https://passport2.chaoxing.com/"
        async with self.browser_manager.new_context(with_cookies=False) as context:
            page = await context.new_page()
            success = await self.login_strategy.login(page, login_url)
            if success:
                self.cookies = await self.login_strategy.get_cookies(page)
                self.browser_manager.set_cookies(self.cookies)
                logging.info("Login succeeded, cookies captured")
            return success

    async def _get_all_homework_tasks(self) -> List[Dict[str, Any]]:
        """Collect homework tasks across all configured courses."""
        all_tasks: List[Dict[str, Any]] = []
        course_urls = getattr(self.config, "course_urls", []) or []
        if not course_urls:
            logging.warning("No course URLs configured")
            return all_tasks

        for index, course_url in enumerate(course_urls, 1):
            logging.info("Processing course %s/%s", index, len(course_urls))
            try:
                tasks = await self._get_course_tasks(course_url)
                all_tasks.extend(tasks)
                logging.info("Course tasks collected: %s", len(tasks))
            except Exception as exc:
                logging.error("Failed to fetch course tasks: %s", exc)
        return all_tasks

    async def _get_course_tasks(self, course_url: str) -> List[Dict[str, Any]]:
        """Fetch homework tasks for a single course."""
        tasks: List[Dict[str, Any]] = []
        if not self.browser_manager:
            raise RuntimeError("Browser manager is not initialized")
        async with self.browser_manager.new_context() as context:
            page = await context.new_page()
            client = CrawlerClient(page)
            await client.setup_response_capture(["mooc2-ans/work/list"])
            await client.goto(course_url)
            await page.wait_for_timeout(2000)

            list_url = client.get_captured_url("mooc2-ans/work/list")
            if not list_url:
                logging.error("Failed to capture homework list URL")
                return tasks

            class_list = getattr(self.config, "class_list", []) or []
            if class_list:
                tasks = await self._get_tasks_by_classes(client, list_url, class_list)
            else:
                tasks = await self._parse_all_pages(client, list_url)
        return tasks

    async def _get_tasks_by_classes(
        self,
        client: CrawlerClient,
        list_url: str,
        class_list: List[str],
    ) -> List[Dict[str, Any]]:
        """Fetch homework tasks for specified class names."""
        tasks: List[Dict[str, Any]] = []
        html = await client.fetch_html(list_url)
        class_id_map = self._parse_class_id_map(html)
        if not class_id_map:
            logging.warning("Class ID map missing; falling back to default list")
            return await self._parse_all_pages(client, list_url)

        for class_name in class_list:
            class_id = class_id_map.get(class_name)
            if not class_id:
                logging.warning("Class not found in page")
                continue
            class_url = self._construct_class_url(list_url, class_id)
            class_tasks = await self._parse_all_pages(client, class_url)
            tasks.extend(class_tasks)
        return tasks

    async def _parse_all_pages(self, client: CrawlerClient, list_url: str) -> List[Dict[str, Any]]:
        """Parse all pages of a homework list."""
        tasks: List[Dict[str, Any]] = []
        page_num = 1
        while True:
            url = convert_url(list_url, page_num)
            html = await client.fetch_html(url)
            page_tasks = self._parse_homework_list(html)
            if not page_tasks:
                break
            tasks.extend(page_tasks)
            page_num += 1
        return tasks

    def _parse_class_id_map(self, html: str) -> Dict[str, str]:
        """Parse class name to ID mapping from HTML."""
        class_map: Dict[str, str] = {}
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select("li.classli"):
            name = item.get("title", "").strip()
            class_id = item.get("data", "")
            if name and class_id:
                class_map[name] = class_id
        return class_map

    def _parse_homework_list(self, html: str) -> List[Dict[str, Any]]:
        """Parse homework tasks from list HTML."""
        tasks: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html, "html.parser")

        null_data = soup.find("div", class_="nullData")
        if null_data and "暂无数据" in null_data.text:
            return tasks

        work_items = soup.find_all("li", id=lambda x: x and x.startswith("work"))
        homework_name_list = getattr(self.config, "homework_name_list", []) or []
        min_ungraded = getattr(self.config, "min_ungraded_students", 0)

        for item in work_items:
            task = self._parse_work_item(item)
            if not task:
                continue
            if homework_name_list and task["作业名"] not in homework_name_list:
                continue
            if min_ungraded is not None and int(min_ungraded) >= 0:
                if task.get("pending_count", 0) <= int(min_ungraded):
                    continue
            tasks.append(task)
        return tasks

    def _parse_work_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """Extract homework task fields from a list item."""
        try:
            class_div = item.find("div", class_="list_class")
            if not class_div:
                return None
            class_name = class_div.get("title", "").strip()

            title_h2 = item.find("h2", class_="list_li_tit")
            if not title_h2:
                return None
            homework_name = title_h2.text.strip()

            time_p = item.find("p", class_="list_li_time")
            time_span = time_p.find("span") if time_p else None
            answer_time = time_span.text.strip() if time_span else ""

            pending_em = item.find("em", class_="fs28")
            try:
                pending_count = int(pending_em.text.strip()) if pending_em else 0
            except ValueError:
                pending_count = 0

            review_a = item.find("a", class_="piyueBtn")
            if not review_a or "href" not in review_a.attrs:
                return None
            review_url = "https://mooc2-ans.chaoxing.com" + review_a["href"]

            save_path = os.path.join(
                "homework",
                sanitize_folder_name(class_name),
                sanitize_folder_name(f"{homework_name}{answer_time}"),
            )
            return {
                "班级": class_name,
                "作业名": homework_name,
                "作答时间": answer_time,
                "作业批阅链接": review_url,
                "save_path": save_path,
                "pending_count": pending_count,
            }
        except Exception as exc:
            logging.error("Failed to parse homework item: %s", exc)
            return None

    async def _process_homework(self, task: Dict[str, Any], max_workers: int) -> Optional[Path]:
        """Process a single homework task and persist results."""
        if not self.browser_manager:
            raise RuntimeError("Browser manager is not initialized")
        save_path = Path(task["save_path"])
        try:
            async with self.browser_manager.new_context() as context:
                processor = HomeworkProcessor(context, max_concurrent=max_workers)
                student_data = await processor.get_all_students_data(task["作业批阅链接"])
                if not student_data:
                    logging.warning("No student data for homework")
                    return None
                final_result = processor.format_results(student_data)
                save_path.mkdir(parents=True, exist_ok=True)
                answer_file = save_path / "answer.json"
                with open(answer_file, "w", encoding="utf-8") as handle:
                    json.dump(final_result, handle, ensure_ascii=False, indent=2)
                logging.info("Homework saved: %s", save_path)
                return save_path
        except Exception as exc:
            logging.error("Failed to process homework: %s", exc)
            return None

    def _construct_class_url(self, base_url: str, class_id: str) -> str:
        """Build a class-specific list URL."""
        if "selectClassid=" in base_url:
            import re

            return re.sub(r"selectClassid=\d+", f"selectClassid={class_id}", base_url)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}selectClassid={class_id}"
