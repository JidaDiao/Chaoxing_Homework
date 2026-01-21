import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

from openai import OpenAI


class LLMError(RuntimeError):
    """Raised when the LLM API request fails."""


@dataclass
class ResponseResult:
    """Structured response output from the LLM."""
    response_id: str
    output_text: str
    parsed_json: Optional[Dict[str, Any]] = None


class LLMClient:
    """LLM client wrapper using the Responses API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model
        logging.getLogger("openai").setLevel(logging.ERROR)

    def create_response(
        self,
        input_content: Union[str, Sequence[Dict[str, Any]]],
        model: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        instructions: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ResponseResult:
        """Create a response using the Responses API."""
        request_params: Dict[str, Any] = {
            "model": model or self.default_model,
            "input": self._normalize_input(input_content),
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if previous_response_id:
            request_params["previous_response_id"] = previous_response_id
        if instructions:
            request_params["instructions"] = instructions

        try:
            response = self.client.responses.create(**request_params)
        except Exception as exc:
            logging.error("Responses API call failed: %s", exc)
            raise LLMError(str(exc)) from exc

        output_text = self._extract_output_text(response)
        parsed_json = self._extract_json(output_text)

        return ResponseResult(
            response_id=response.id,
            output_text=output_text,
            parsed_json=parsed_json,
        )

    def create_context(
        self,
        system_instructions: str,
        context_content: Sequence[Dict[str, Any]],
        model: Optional[str] = None,
    ) -> str:
        """Create a reusable context and return its response id."""
        result = self.create_response(
            input_content=context_content,
            model=model or self.default_model,
            instructions=system_instructions,
            temperature=0.3,
        )
        logging.info("Context created with response_id=%s", result.response_id)
        return result.response_id

    def _normalize_input(
        self, input_content: Union[str, Sequence[Dict[str, Any]]]
    ) -> Union[str, List[Dict[str, Any]]]:
        if isinstance(input_content, str):
            return input_content

        if not input_content:
            return []

        first_item = input_content[0]
        if isinstance(first_item, dict) and ("role" in first_item or first_item.get("type") == "message"):
            return [self._normalize_message(item) for item in input_content if isinstance(item, dict)]

        content_items = [self._normalize_content_item(item) for item in input_content if isinstance(item, dict)]
        return [
            {
                "type": "message",
                "role": "user",
                "content": content_items,
            }
        ]

    def _normalize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            normalized_content = [self._normalize_content_item(item) for item in content if isinstance(item, dict)]
        else:
            normalized_content = [{"type": "input_text", "text": str(content)}]

        return {
            "type": "message",
            "role": role,
            "content": normalized_content,
        }

    def _normalize_content_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item_type = item.get("type")
        if item_type == "input_text":
            return item
        if item_type == "input_image":
            if "detail" not in item:
                item = dict(item)
                item["detail"] = "auto"
            return item
        if item_type in {"text", "output_text"}:
            return {"type": "input_text", "text": item.get("text", "")}
        if item_type == "image_url":
            image_url = item.get("image_url")
            if isinstance(image_url, dict):
                image_url = image_url.get("url")
            if not image_url:
                return {"type": "input_text", "text": "[image missing]"}
            return {
                "type": "input_image",
                "image_url": image_url,
                "detail": "auto",
            }
        if item_type == "image_placeholder":
            placeholder = item.get("image_id")
            return {
                "type": "input_text",
                "text": f"[image placeholder {placeholder}]" if placeholder else "[image placeholder]",
            }
        return {"type": "input_text", "text": str(item)}

    def _extract_output_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text

        output_items = getattr(response, "output", None)
        if not output_items:
            return ""

        parts: List[str] = []
        for item in output_items:
            content = getattr(item, "content", None) or getattr(item, "content", [])
            for part in content or []:
                part_type = getattr(part, "type", None) or part.get("type")
                if part_type == "output_text":
                    text = getattr(part, "text", None) or part.get("text", "")
                    parts.append(text)
        return "".join(parts)

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        markdown_json_pattern = r"```(?:json)?\s*\n([\s\S]*?)\n```"
        for match in re.findall(markdown_json_pattern, text):
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        for idx, char in enumerate(text[start:], start=start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : idx + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

        return None
