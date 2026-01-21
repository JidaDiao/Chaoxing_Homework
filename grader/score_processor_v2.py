import logging
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, Iterable, List, Optional

from utils import download_image
from .llm_client import LLMClient, ResponseResult


class GradingError(RuntimeError):
    """Raised when grading flow cannot proceed."""


@dataclass
class GradingContext:
    """Grading session context for a single homework."""
    homework_id: str
    context_response_id: Optional[str] = None
    grading_response_id: Optional[str] = None
    grading_standard: str = ""


@dataclass
class StudentScore:
    """Student scoring result."""
    name: str
    score: float
    criteria: str = ""
    success: bool = True
    error: str = ""


class ScoreProcessorV2:
    """Score processor using Responses API with reusable session context."""

    MAX_RETRIES = 10

    def __init__(
        self,
        llm_client: LLMClient,
        prepare_model: str,
        gen_model: str,
        batch_size: int = 3,
        on_score_update: Optional[Callable[[Dict[str, Dict[str, Any]], List[str]], None]] = None,
    ) -> None:
        self.llm_client = llm_client
        self.prepare_model = prepare_model
        self.gen_model = gen_model
        self.batch_size = max(3, min(5, batch_size))
        self.on_score_update = on_score_update

        self._lock = Lock()
        self._context: Optional[GradingContext] = None
        self._scores: Dict[str, StudentScore] = {}
        self._uncorrected: Dict[str, List[Dict[str, Any]]] = {}
        self._corrected: Dict[str, List[Dict[str, Any]]] = {}

    def set_student_answers(
        self,
        uncorrected: Dict[str, List[Dict[str, Any]]],
        corrected: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        final_scores: Optional[Dict[str, Any]] = None,
        grading_standard: Optional[str] = None,
    ) -> None:
        """Set current homework answers and existing scores."""
        self._uncorrected = uncorrected
        self._corrected = corrected or {}
        self._scores = {}

        if final_scores:
            for name, data in final_scores.items():
                if isinstance(data, dict):
                    score = data.get("score", 0)
                    criteria = data.get("scoring_criteria", "")
                else:
                    score = data
                    criteria = ""
                self._scores[name] = StudentScore(
                    name=name,
                    score=float(score),
                    criteria=str(criteria or ""),
                )

        if grading_standard:
            self._context = GradingContext(
                homework_id="",
                grading_standard=grading_standard,
            )

    def initialize_context(self, homework_data: Dict[str, Any], homework_id: str) -> GradingContext:
        """Initialize a reusable grading context for a homework."""
        context_content = self._build_homework_content(homework_data)
        instructions = (
            "你是一名教师，负责评阅学生作业。"
            "我会先提供题目信息和参考答案，然后逐步发送学生的作答。"
            "请仔细阅读并理解每道题目的要求和评分要点。"
        )

        context_id = self.llm_client.create_context(
            system_instructions=instructions,
            context_content=context_content,
            model=self.prepare_model,
        )

        self._context = GradingContext(
            homework_id=homework_id,
            context_response_id=context_id,
            grading_standard=self._context.grading_standard if self._context else "",
        )
        logging.info("Grading context initialized for homework_id=%s", homework_id)
        return self._context

    def attach_grading_standard(self, grading_standard: str) -> str:
        """Attach an existing grading standard to the current session."""
        if not self._context or not self._context.context_response_id:
            raise GradingError("Context must be initialized before attaching grading standard")

        input_content = [
            {
                "type": "text",
                "text": f"以下是本次评分标准，请牢记并用于后续评分。\n{grading_standard}",
            }
        ]
        instructions = "请确认已理解评分标准，不需要展开说明。"

        result = self.llm_client.create_response(
            input_content=input_content,
            model=self.prepare_model,
            previous_response_id=self._context.context_response_id,
            instructions=instructions,
            temperature=0.3,
        )

        self._context.grading_response_id = result.response_id
        self._context.grading_standard = grading_standard
        logging.info("Existing grading standard attached with response_id=%s", result.response_id)
        return result.response_id

    def generate_grading_standard(self, sample_students: Dict[str, List[Dict[str, Any]]], number: int) -> str:
        """Generate grading standard and sample scores in one call."""
        if not self._context or not self._context.context_response_id:
            raise GradingError("Context must be initialized before generating grading standard")

        input_content = self._build_students_content(sample_students)
        instructions = (
            f"基于前面的题目信息，现在提供 {number} 名学生的作答。\n"
            "请完成以下任务：\n"
            "1. 分析学生整体水平\n"
            "2. 制定评分标准\n"
            "3. 为每位学生打分并给出评分依据\n"
            "\n输出要求：\n"
            "- 评分标准要详细、可操作、可解释\n"
            "- 分数要客观反映学生水平，有适当区分度\n"
            f"- 必须为所有 {number} 名学生打分\n"
            "\n输出格式（严格 JSON）：\n"
            "{\n"
            "  \"grading_standard\": \"...\",\n"
            "  \"student_scores\": {\n"
            "    \"张三\": {\"score\": 85, \"scoring_criteria\": \"...\"}\n"
            "  }\n"
            "}"
        )

        best_result: Optional[ResponseResult] = None
        best_count = 0

        for attempt in range(self.MAX_RETRIES):
            try:
                result = self.llm_client.create_response(
                    input_content=input_content,
                    model=self.prepare_model,
                    previous_response_id=self._context.context_response_id,
                    instructions=instructions,
                    temperature=0.5,
                )
            except Exception as exc:
                logging.error("Generate grading standard failed (attempt %s): %s", attempt + 1, exc)
                continue

            parsed = result.parsed_json or {}
            scores = parsed.get("student_scores", {}) if isinstance(parsed, dict) else {}
            standard = parsed.get("grading_standard", "") if isinstance(parsed, dict) else ""

            if standard and len(scores) > best_count:
                best_result = result
                best_count = len(scores)

            if standard and len(scores) >= max(1, int(number * 0.8)):
                best_result = result
                break

        if not best_result or not best_result.parsed_json:
            raise GradingError(f"Failed to generate grading standard after {self.MAX_RETRIES} retries")

        parsed = best_result.parsed_json
        standard = parsed.get("grading_standard", "")
        if not standard:
            raise GradingError("Grading standard missing in response")

        self._context.grading_response_id = best_result.response_id
        self._context.grading_standard = standard

        scores = parsed.get("student_scores", {}) if isinstance(parsed, dict) else {}
        for name, data in scores.items():
            if isinstance(data, dict):
                score_value = data.get("score", 0)
                criteria = data.get("scoring_criteria", "")
            else:
                score_value = data
                criteria = ""
            self._save_score(
                StudentScore(
                    name=name,
                    score=float(score_value),
                    criteria=str(criteria or ""),
                )
            )

        logging.info("Grading standard generated with %s sample scores", len(scores))
        return standard

    def grade_students_batch(self, students: Dict[str, List[Dict[str, Any]]]) -> List[StudentScore]:
        """Grade students in batches using the current session."""
        if not students:
            return []

        if not self._context or not self._context.grading_response_id:
            raise GradingError("Grading standard must be prepared before batch grading")

        student_items = list(students.items())
        results: List[StudentScore] = []

        for start in range(0, len(student_items), self.batch_size):
            batch = dict(student_items[start : start + self.batch_size])
            results.extend(self._grade_batch(batch))

        return results

    def get_all_scores(self) -> Dict[str, Dict[str, Any]]:
        """Return all scores in legacy schema."""
        with self._lock:
            return {
                name: {"score": score.score, "scoring_criteria": score.criteria}
                for name, score in self._scores.items()
            }

    def get_final_scores(self) -> Dict[str, Dict[str, Any]]:
        """Return all scores for persistence."""
        return self.get_all_scores()

    def get_grading_standard(self) -> str:
        """Return grading standard text."""
        return self._context.grading_standard if self._context else ""

    def get_uncorrected_answers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return remaining ungraded answers."""
        return self._uncorrected

    def remove_uncorrected(self, student_names: Iterable[str]) -> None:
        """Remove students from the uncorrected pool."""
        for name in student_names:
            self._uncorrected.pop(name, None)

    def normalize_score(
        self,
        student_scores: Dict[str, float],
        normalized_min: float = 60,
        normalized_max: float = 85,
        original_min: float = 20,
        original_max: float = 90,
    ) -> Dict[str, float]:
        """Normalize scores using the legacy scaling rules."""
        def scale_score(score: float) -> float:
            if score < original_min or score > original_max:
                return score
            return score / 100 * (normalized_max - normalized_min) + normalized_min

        return {name: scale_score(score) for name, score in student_scores.items()}

    def _build_homework_content(self, homework_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []

        for question_id, question in homework_data.get("题目", {}).items():
            text_parts = question.get("题干", {}).get("text", [])
            stem = " ".join(text_parts) if isinstance(text_parts, list) else str(text_parts)
            correct = question.get("正确答案", "")
            content.append(
                {
                    "type": "text",
                    "text": f"{question_id}:\n题干: {stem}\n参考答案: {correct}",
                }
            )

            for img_url in question.get("题干", {}).get("images", []) or []:
                img_base64 = download_image(img_url)
                if img_base64:
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}",
                            },
                        }
                    )
                else:
                    content.append({"type": "text", "text": "[参考图下载失败]"})

        return content

    def _build_students_content(self, students: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []

        for name, messages in students.items():
            content.append({"type": "text", "text": f"\n===== 学生: {name} ====="})
            content.extend(self._flatten_message_content(messages))

        return content

    def _flatten_message_content(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                items.extend(content)
            elif isinstance(content, str):
                items.append({"type": "text", "text": content})
        return items

    def _grade_batch(self, students: Dict[str, List[Dict[str, Any]]]) -> List[StudentScore]:
        names = list(students.keys())
        remaining = names[:]
        results: Dict[str, StudentScore] = {}

        for attempt in range(self.MAX_RETRIES):
            if not remaining:
                break

            batch_students = {name: students[name] for name in remaining}
            input_content = self._build_students_content(batch_students)
            instructions = (
                f"基于前面的评分标准和参考样本，为以下 {len(remaining)} 名学生评分。\n"
                f"学生：{', '.join(remaining)}\n"
                "要求：\n"
                "1. 严格按照评分标准打分\n"
                "2. 保持分数一致性\n"
                "3. 为每位学生提供评分依据\n"
                "\n输出格式（严格 JSON）：\n"
                "{\n"
                "  \"student_scores\": {\n"
                "    \"张三\": {\"score\": 80, \"scoring_criteria\": \"...\"}\n"
                "  }\n"
                "}"
            )

            try:
                result = self.llm_client.create_response(
                    input_content=input_content,
                    model=self.gen_model,
                    previous_response_id=self._context.grading_response_id,
                    instructions=instructions,
                    temperature=0.6,
                )
            except Exception as exc:
                logging.error("Batch grading failed (attempt %s): %s", attempt + 1, exc)
                continue

            parsed = result.parsed_json if isinstance(result.parsed_json, dict) else {}
            scores = parsed.get("student_scores", parsed) if isinstance(parsed, dict) else {}
            if not scores:
                continue

            newly_scored: List[str] = []
            for name in remaining:
                if name not in scores:
                    continue
                data = scores[name]
                if isinstance(data, dict):
                    score_value = data.get("score", 0)
                    criteria = data.get("scoring_criteria", "")
                else:
                    score_value = data
                    criteria = ""

                score = StudentScore(
                    name=name,
                    score=float(score_value),
                    criteria=str(criteria or ""),
                )
                results[name] = score
                self._save_score(score)
                newly_scored.append(name)

            remaining = [name for name in remaining if name not in newly_scored]

        for name in remaining:
            score = StudentScore(
                name=name,
                score=0,
                success=False,
                error=f"评分失败，已重试 {self.MAX_RETRIES} 次",
            )
            results[name] = score
            self._save_score(score)

        return [results[name] for name in names if name in results]

    def _save_score(self, score: StudentScore) -> None:
        with self._lock:
            self._scores[score.name] = score
            if self.on_score_update:
                payload = {
                    name: {"score": item.score, "scoring_criteria": item.criteria}
                    for name, item in self._scores.items()
                }
                self.on_score_update(payload, [score.name])
