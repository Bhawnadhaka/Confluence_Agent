# modules/story_generator/gpt_backend.py
from openai import AzureOpenAI
from .config import StoryConfig


class ConfluenceStoryGenerator:
    """
    GPT backend used by DocxSections and ConfluenceAgent.
    Central location for all GPT calls.
    """

    def __init__(self, config: StoryConfig):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config.azure_openai_key,
            api_version=config.azure_api_version,
            azure_endpoint=config.azure_openai_endpoint
        )

    def generate_step_heading(self, frame_summary: str) -> str:
        """Generate concise step heading (5-6 words)."""
        prompt = f"""
        Create a concise step heading of 5-6 words maximum from this screen description:
        "{frame_summary}"
        
        Return only the heading text, no quotes or additional text.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=30,
                temperature=0.3
            )
            heading = response.choices[0].message.content.strip()
            return " ".join(heading.split()[:6])
        except Exception:
            return " ".join(frame_summary.split()[:6])
