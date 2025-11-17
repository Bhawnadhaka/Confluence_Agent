import logging
import time
from typing import Dict, List, Callable, Tuple

log = logging.getLogger(__name__)


class InteractionManager:

    def __init__(
        self,
        data: Dict[str, Dict],
        azure_client,
        prompt_selector: Callable[[str], Tuple[str, str]],
        batch_size: int = 6,
        inter_batch_sleep: float = 1.2
    ):
        self.data = data or {}
        self.azure = azure_client
        self.prompt_selector = prompt_selector
        self.batch_size = batch_size
        self.inter_batch_sleep = inter_batch_sleep

    def _is_valid_url(self, url: str) -> bool:
        return isinstance(url, str) and url.startswith(("http://", "https://"))

    def _classify_url(self, url: str) -> str:
        if url in self.data:
            return "frame"

        for frame_val in self.data.values():
            for el in frame_val.get("elements", []):
                if el.get("from_url") == url:
                    return "element"
                if el.get("to_url") == url:
                    return "destination"

        return "general"

    def collect_interaction_groups(self) -> List[Dict]:
        groups = []

        for frame_url, frame_data in self.data.items():

            urlset = {frame_url} if self._is_valid_url(frame_url) else set()

            for element in frame_data.get("elements", []):
                if self._is_valid_url(element.get("from_url")):
                    urlset.add(element["from_url"])
                if self._is_valid_url(element.get("to_url")):
                    urlset.add(element["to_url"])

            groups.append({
                "frame_url": frame_url,
                "urls": list(urlset),
                "element_count": len(frame_data.get("elements", []))
            })

        groups.sort(key=lambda x: x["element_count"])
        return groups

    def process_groups(self, groups: List[Dict]):
        """ ALWAYS summarize fresh. No caching. """
        summary_map = {}

        for group in groups:
            urls = group["urls"]

            for i in range(0, len(urls), self.batch_size):
                batch = urls[i:i + self.batch_size]

                for url in batch:
                    url_type = self._classify_url(url)
                    system_prompt, user_prompt = self.prompt_selector(url_type)
                    summary = self.azure.summarize(url, system_prompt, user_prompt)
                    summary_map[url] = summary or ""

                if i + self.batch_size < len(urls):
                    time.sleep(self.inter_batch_sleep)

        return summary_map
