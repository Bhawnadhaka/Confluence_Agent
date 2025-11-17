import re
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

class ClickUpTaskExtractor:

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, clickup_token: str):
        self.clickup_token = clickup_token
        self.headers = {
            "Authorization": self.clickup_token,
            "Content-Type": "application/json",
        }

    def fetch_task_enhanced(self, task_id: str) -> dict | None:
        """Fetch ClickUp task details, attachments, assignees, Figma link, and cleaned comments."""
        task_data = self._get_task(task_id)
        if not task_data:
            return None

        def remove_mentions(text):
            return re.sub(r'@[\w\-\.]+', '', text).strip()

        title = task_data.get("name", "")
        description = task_data.get("description", "")

        # Assignees as list of usernames
        assignees = [a.get("username", "Unknown") for a in task_data.get("assignees", [])]

        # Figma link
        figma_link = self._extract_figma_link(task_data)

        # Attachments extraction
        attachments = self._extract_attachments(task_data)

        # Comments extraction and cleaning
        comments_raw = self._get_comments(task_id)
        comments = []
        for c in comments_raw:
            cleaned_content = remove_mentions(c.get("content", ""))
            if cleaned_content:
                comments.append(
                    {
                        "user": c.get("user", "Unknown"),
                        "content": cleaned_content,
                        "date": c.get("date"),
                    }
                )

        # Split description if needed
        parts = description.split("Business Case", 1)
        description_part1 = parts[0].strip() if parts else ""
        business_case = parts[1].strip() if len(parts) > 1 else ""

        task_info = {
            "task_id": task_id,
            "title": title,
            "description_part1": description_part1,
            "business_case": business_case,
            "assignees": assignees,
            "figma_link": figma_link,
            "attachments": attachments,
            "comments": comments,
        }

        return task_info

    def _get_task(self, task_id: str) -> dict | None:
        url = f"{self.BASE_URL}/task/{task_id}"
        params = {"include_comments": "true", "attachments": "true"}
        response = requests.get(url, headers=self.headers, params=params, timeout=20)
        if response.status_code != 200:
            return None
        return response.json()

    def _extract_figma_link(self, task_data: dict) -> str | None:
        for field in task_data.get("custom_fields", []):
            name = (field.get("name") or "").lower()
            if "figma" not in name:
                continue
            value = field.get("value")
            if isinstance(value, dict):
                value = value.get("url")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_attachments(self, task_data: dict) -> list[dict]:
        attachments = []
        for att in task_data.get("attachments", []):
            title = att.get("title", "Unnamed")
            # Use real download URL if it exists, otherwise fall back to manual construction
            url = att.get('url') or f"https://app.clickup.com/attachment/{att.get('id')}"
            attachment_info = {
                "name": title,
                "type": att.get("extension", "unknown"),
                "url": url,
                "is_design_file": any(
                    ext in title.lower()
                    for ext in [".fig", ".png", ".jpg", ".svg", ".pdf", ".doc", ".docx"]
                ),
            }
            attachments.append(attachment_info)
        return attachments

    def _get_comments(self, task_id: str) -> list[dict]:
        comments_url = f"{self.BASE_URL}/task/{task_id}/comment"
        comments = []
        next_page = None

        while True:
            params = {"page": next_page} if next_page else {}
            response = requests.get(comments_url, headers=self.headers, params=params, timeout=20)
            if response.status_code != 200:
                break
            data = response.json()
            for c in data.get("comments", []):
                text = c.get("comment_text", "")
                if isinstance(text, list):
                    text = " ".join(
                        t.get("text", "") for t in text if isinstance(t, dict)
                    )
                comments.append(
                    {
                        "user": c.get("user", {}).get("username", "Unknown"),
                        "content": text.strip(),
                        "date": c.get("date"),
                    }
                )
            next_page = data.get("next_page")
            if not next_page:
                break

        comments.sort(key=lambda x: x.get("date") or 0)
        return comments

    def save_clickup_data(self, data: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("data/clickup", exist_ok=True)
        filename = f"data/clickup/clickup_task_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return filename

# Optional standalone usage
if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("CLICKUP_API_TOKEN")
    extractor = ClickUpTaskExtractor(token)
    task_id = input("Enter ClickUp Task ID: ").strip()
    result = extractor.fetch_task_enhanced(task_id)
    if result:
        saved_path = extractor.save_clickup_data(result)
        print(f"Saved to {saved_path}")
