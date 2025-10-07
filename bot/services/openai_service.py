from __future__ import annotations

import os
from base64 import b64decode
from datetime import datetime
from typing import Optional, Tuple

from openai import OpenAI


DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_IMAGE_SIZE = "1024x1024"


class OpenAIService:
    """Thin wrapper around the OpenAI SDK for text and image generation.

    Args:
        api_key: Optional API key. If omitted, reads OPENAI_API_KEY from the env.
        log_dir: Base directory used when saving generated images from base64.

    Notes:
        - `chat()` returns a plain string (or None on failure).
        - `image()` returns (url_or_path, error_message). If the API returns a URL,
          that is preferred; otherwise, the base64 payload is saved as a PNG under
          `<log_dir>/images/` and the local path is returned.
    """

    def __init__(self, api_key: str | None = None, log_dir: str = "logs") -> None:
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = OpenAI(api_key=key)
        self._log_dir = log_dir
        if not key:
            # Not fatal—methods will still run and raise within try/except—but this helps debugging.
            print("OpenAIService: WARNING: OPENAI_API_KEY is not set.")

    # ---------- Text ----------

    def chat(
        self,
        prompt: str,
        model: str = DEFAULT_CHAT_MODEL,
        temperature: float = 1.2,
        timeout: Optional[float] = 30.0,
    ) -> Optional[str]:
        """Generate a short text response for the given prompt.

        Args:
            prompt: System-style instruction. (Kept simple for your use case.)
            model: Model name to use.
            temperature: Sampling temperature.
            timeout: Optional request timeout in seconds.

        Returns:
            The model’s text response, stripped, or None on failure.
        """
        try:
            resp = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": prompt}],
                temperature=temperature,
                timeout=timeout,  # supported by OpenAI python client
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            print("OpenAI error:", e)
            return None

    # ---------- Image ----------

    def image(
        self,
        prompt: str,
        size: str = DEFAULT_IMAGE_SIZE,
        timeout: Optional[float] = 60.0,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate an image for the given prompt.

        Args:
            prompt: Natural language description of the desired image.
            size: Image size (e.g., '1024x1024').
            timeout: Optional request timeout in seconds.

        Returns:
            (url_or_path, error):
              - If API returns a hosted URL, (url, None)
              - If API returns base64, (local_file_path, None)
              - On failure/missing data, (None, error_message)
        """
        try:
            resp = self._client.images.generate(
                prompt=prompt, size=size, timeout=timeout
            )
            data = resp.data[0]

            # Prefer a hosted URL if present
            url = getattr(data, "url", None)
            if url:
                return url, None

            # Otherwise handle base64 payload
            b64 = getattr(data, "b64_json", None)
            if b64:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out = os.path.join(self._log_dir, "images")
                os.makedirs(out, exist_ok=True)
                path = os.path.join(out, f"image_{ts}.png")
                with open(path, "wb") as f:
                    f.write(b64decode(b64))
                return path, None

            return None, "No image data returned."
        except Exception as e:
            print("OpenAI image error:", e)
            return None, "Image generation failed."
