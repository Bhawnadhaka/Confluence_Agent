# summarizer/azure_client.py
import time
import logging
from typing import Optional
from openai import AzureOpenAI
from configg import get_secret

log = logging.getLogger(__name__)


class AzureVisionClient:
    
    def __init__(self, model_name: str = None, api_key: str = None, azure_endpoint: str = None, api_version: str = None):
        # Try parameters first, then fall back to config (works for local and cloud)
        self.api_key = api_key or get_secret("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or get_secret("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or get_secret("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.model_name = model_name or get_secret("AZURE_OPENAI_MODEL_NAME")
        
        if not (self.api_key and self.azure_endpoint and self.model_name):
            raise ValueError("Azure credentials and model must be provided")
        
        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            api_version=self.api_version
        )
        self.log = logging.getLogger(__name__)

    def summarize(self, url: str, system_prompt: str, user_prompt: str, max_retries: int = 3, timeout: int = 300) -> Optional[str]:
        if not url:
            return None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {"type": "image_url", "image_url": {"url": url}},
                            ],
                        },
                    ],
                    temperature=0.4,
                    max_tokens=4096,
                    timeout=timeout
                )
                # best-effort extraction
                choice = getattr(response, "choices", None)
                if choice:
                    try:
                        return response.choices[0].message.content.strip()
                    except Exception:
                        pass
                # fallback: try JSON structure
                data = getattr(response, "to_dict", lambda: {})()
                text = None
                try:
                    text = data.get("choices", [])[0].get("message", {}).get("content", "").strip()
                except Exception:
                    text = None
                return text or None

            except Exception as exc:
                self.log.warning("Azure summarize attempt %s/%s failed for %s: %s", attempt, max_retries, url, exc)
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)
                else:
                    self.log.error("Azure summarize final failure for %s: %s", url, exc)
                    return None