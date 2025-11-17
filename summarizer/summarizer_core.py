import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from .azure_client import AzureVisionClient
from .interaction_manager import InteractionManager

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


class SummarizerCore:

    def __init__(self, figma_data: Dict[str, Any]):
        import os

        self.data = figma_data or {}

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        model_name = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")

        if not api_key or not endpoint:
            raise ValueError("Azure credentials missing.")

        self.azure_client = AzureVisionClient(
            model_name=model_name,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )

        # Interaction manager WITHOUT CACHE
        self.manager = InteractionManager(
            data=self.data,
            azure_client=self.azure_client,
            prompt_selector=self._prompt_selector
        )

    def _prompt_selector(self, url_type: str):
        if url_type == "frame":
            return (
                "You are an expert UX design analyst focusing on full-screen UI layout understanding.",
                "Analyze this full screen UI design: 1. Purpose? 2. Key components? 3. Visual hierarchy? Keep under 100 words."
            )

        elif url_type == "element":
            return (
                "You are a UI element recognizer identifying clickable controls or icons.",
                "Analyze this UI element: 1. What is it? 2. Why? 3. Visual cues? Under 60 words."
            )

        elif url_type == "destination":
            return (
                "You analyze UI screens navigated after user actions.",
                "Analyze destination screen: 1. What happened? 2. What is displayed? 3. Differences? Under 80 words."
            )

        return (
            "You are a UX design summarizer.",
            "Describe this image briefly in under 60 words."
        )

    
    def run(self) -> Dict[str, Any]:
        log.info("🔹 Starting summarization ...")

        # collect grouped URLs
        groups = self.manager.collect_interaction_groups()

        # summarize all URLs fresh
        url_summary_map = self.manager.process_groups(groups)

        screens_output = []

        for group in groups:
            frame_url = group.get("frame_url")
            elements = self.data.get(frame_url, {}).get("elements", [])

            interactions = []
            for el in elements:
                interactions.append({
                    "from_summary": url_summary_map.get(el.get("from_url"), ""),
                    "to_summary": url_summary_map.get(el.get("to_url"), ""),
                    "to_url": el.get("to_url")
                })

            screens_output.append({
                "frame_url": frame_url,
                "frame_summary": url_summary_map.get(frame_url, ""),
                "interactions": interactions
            })

        final_output = {
            "metadata": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "total_screens": len(screens_output)
            },
            "screens": screens_output
        }

        return final_output

