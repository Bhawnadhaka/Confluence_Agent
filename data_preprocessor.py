import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


class Preprocessor:
    def __init__(self, clickup_data: Dict[str, Any], figma_data: Dict[str, Any], save_clickup: bool = False):
        self.clickup_data = clickup_data or {}
        self.figma_data = figma_data or {}
        self.save_clickup = save_clickup

        # Internal memory containers
        self.frame_registry: Dict[str, Any] = {}
        self.clickup_context: Dict[str, Any] = {}

        # Directory only for clickup saves (no cache)


    def preprocess_figma_data(self) -> Dict[str, Any]:
        """
        Cleans and structures Figma prototype interactions into a 
        deduplicated frame-element mapping for summarization.
        """
        log.info("STEP 1: Preprocessing Figma data")

        interactions: List[Dict[str, Any]] = self.figma_data.get("interactions", [])
        if not interactions:
            log.warning(" No Figma interactions found.")
            return {}

        frame_map: Dict[str, Dict[str, Any]] = {}

        for inter in interactions:
            from_frame = inter.get("from_frame_url")
            if not from_frame:
                continue

            if from_frame not in frame_map:
                frame_map[from_frame] = {"elements": []}

            frame_map[from_frame]["elements"].append({
                "from_name": inter.get("from_name"),
                "to_name": inter.get("to_name"),
                "from_url": inter.get("from_url"),
                "to_url": inter.get("to_url"),
                "animation": inter.get("animation", "Instant"),
            })

        self.frame_registry = frame_map
        log.info(f"✓ Processed {len(frame_map)} unique Figma frames.")
        return frame_map

    def preprocess_clickup_data(self) -> Dict[str, Any]:
        """
        Extracts and cleans ClickUp context: title, description,
        comments, attachments, and optional Figma link.
        """
        log.info("STEP 2: Preprocessing ClickUp data")

        title = self.clickup_data.get("title", "")
        desc = self.clickup_data.get("description", "")
        comments = self.clickup_data.get("comments", []) or []
        attachments = [a.get("url") for a in self.clickup_data.get("attachments", [])]
        assignees = self.clickup_data.get("assignees", [])
        figma_link = self.clickup_data.get("figma_link", "")

        # Split description intelligently
        parts = desc.split("Business Case", 1)
        desc_part1 = parts[0].strip() if parts else ""
        business_case = parts[1].strip() if len(parts) > 1 else ""

        self.clickup_context = {
            "title": title,
            "description_part1": desc_part1,
            "business_case": business_case,
            "comments": [
                {"user": c.get("user", ""), "content": c.get("content", "")}
                for c in comments
            ],
            "attachments": attachments,
            "assignees": assignees,
            "figma_link": figma_link,
        }

        log.info(f"ClickUp context extracted for task: {title or 'Untitled Task'}")
        return self.clickup_context

    def save_clickup_context(self) -> str:
        """Saves ClickUp context to JSON (only when enabled)."""
        filename = os.path.join(
            self.merged_dir,
            f"clickup_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.clickup_context, f, indent=2)
        log.info(f" ClickUp context saved at: {filename}")
        return filename

    def run_all(self) -> Dict[str, Any]:
        log.info("\n Running Unified Data Preprocessing...\n")

        self.preprocess_figma_data()
        self.preprocess_clickup_data()

        if self.save_clickup:
            self.save_clickup_context()

        log.info("\n Preprocessing complete.\n")

        return {
            "figma_processed": self.frame_registry,
            "clickup_processed": self.clickup_context,
        }
