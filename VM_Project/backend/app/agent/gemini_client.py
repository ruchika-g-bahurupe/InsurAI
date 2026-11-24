"""Gemini API Client Wrapper using the modern Google GenAI SDK.

Handles client initialization, request-level timeout configuration,
transient retry handling, connectivity checks, and unified interfaces for
structured JSON output and manual function calling.
"""

import time
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.logging import logger


class GeminiClientWrapper:
    """Enterprise wrapper around Google GenAI SDK Client."""

    def __init__(self):
        self.api_key: str = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.model: str = (settings.GEMINI_MODEL or "gemini-3.8-flash").strip()
        self.analysis_model: str = (settings.GEMINI_ANALYSIS_MODEL or self.model).strip()
        self.temperature: float = settings.GEMINI_TEMPERATURE
        self.max_tokens: int = settings.GEMINI_MAX_OUTPUT_TOKENS
        self._client: Optional[genai.Client] = None
        self.last_error: Optional[str] = None

        if self.is_live():
            try:
                self._client = genai.Client(api_key=self.api_key,
                                            http_options=types.HttpOptions(
                                           timeout=settings.GEMINI_TIMEOUT_MS
                                             ))
                logger.info(f"GeminiClient initialized successfully with model: {self.model}")
            except Exception as e:
                self.last_error = self._sanitize_error(e)
                logger.error(f"Failed to initialize Google GenAI Client: {self.last_error}")
                self._client = None
        else:
            logger.info("GeminiClient: GEMINI_API_KEY is not configured. Running in Degraded/Offline Mode.")

    def is_live(self) -> bool:
        """Returns True if a non-empty, non-dummy GEMINI_API_KEY is configured."""
        key = (self.api_key or "").strip()
        return bool(
            key
            and len(key) > 8
            and not key.startswith("your-gemini")
            and not key.startswith("YOUR_ACTUAL")
        )

    @property
    def client(self) -> Optional[genai.Client]:
        if self._client is None and self.is_live():
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _sanitize_error(self, err: Exception) -> str:
        """Return a safe error string that never leaks the configured API key."""
        msg = str(err)
        if self.api_key:
            msg = msg.replace(self.api_key, "[REDACTED]")
        return msg

    @staticmethod
    def _is_retryable(err: Exception) -> bool:
        msg = str(err).lower()
        return any(k in msg for k in ("429", "503", "500", "rate", "quota", "timeout", "unavailable"))

    def test_connectivity(self, use_analysis_model: bool = False) -> Dict[str, Any]:
        """Safely verify API key and model accessibility without exposing secrets."""
        model_to_use = self.analysis_model if use_analysis_model else self.model
        if not self.is_live() or not self.client:
            return {
                "connected": False,
                "model": model_to_use,
                "error": "GEMINI_API_KEY is not configured.",
            }
        try:
            resp = self.client.models.generate_content(
                model=model_to_use,
                contents="Reply with OK",
                config=types.GenerateContentConfig(
                    max_output_tokens=16,
                    temperature=0.0,
                    http_options=types.HttpOptions(timeout=15000),
                ),
            )
            self.last_error = None
            return {
                "connected": True,
                "model": model_to_use,
                "response_preview": (getattr(resp, "text", None) or "").strip()[:40],
                "error": None,
            }
        except Exception as e:
            self.last_error = self._sanitize_error(e)
            return {
                "connected": False,
                "model": model_to_use,
                "error": self.last_error,
            }

    def generate_structured_analysis(
        self,
        system_instruction: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        use_analysis_model: bool = False,
        timeout_seconds: Optional[float] = 120.0,
    ) -> Optional[str]:
        """Calls Gemini to generate structured output with request-level timeout."""
        self.last_error = None
        if not self.is_live() or not self.client:
            self.last_error = "GEMINI_API_KEY is not configured."
            return None

        model_to_use = self.analysis_model if use_analysis_model else self.model
        http_opts = types.HttpOptions(timeout=max(1000, int(timeout_seconds * 1000))) if timeout_seconds else None
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            response_mime_type="application/json" if response_schema else "text/plain",
            http_options=http_opts,
        )
        if response_schema:
            config.response_schema = response_schema

        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=model_to_use,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except Exception as e:
                self.last_error = self._sanitize_error(e)
                logger.error(f"Gemini generate_structured_analysis failed on {model_to_use} (attempt {attempt}/{max_attempts}): {self.last_error}")
                if attempt < max_attempts and self._is_retryable(e):
                    time.sleep(1.5 * (2 ** (attempt - 1)))
                    continue
                return None
        return None

    def generate_with_tools(
        self,
        system_instruction: str,
        contents: List[Any],
        tools: List[Any],
        use_analysis_model: bool = False,
        timeout_seconds: Optional[float] = 120.0,
    ) -> Optional[Any]:
        """Executes a turn with Gemini manual function calling (AFC disabled) and request-level timeout."""
        self.last_error = None
        if not self.is_live() or not self.client:
            self.last_error = "GEMINI_API_KEY is not configured."
            return None

        model_to_use = self.analysis_model if use_analysis_model else self.model
        http_opts = types.HttpOptions(timeout=max(1000, int(timeout_seconds * 1000))) if timeout_seconds else None
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=http_opts,
        )

        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=model_to_use,
                    contents=contents,
                    config=config,
                )
                return response
            except Exception as e:
                self.last_error = self._sanitize_error(e)
                logger.error(f"Gemini generate_with_tools failed on {model_to_use} (attempt {attempt}/{max_attempts}): {self.last_error}")
                if attempt < max_attempts and self._is_retryable(e):
                    time.sleep(1.5 * (2 ** (attempt - 1)))
                    continue
                return None
        return None


gemini_client = GeminiClientWrapper()
