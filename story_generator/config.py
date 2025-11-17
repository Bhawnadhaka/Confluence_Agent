
from dataclasses import dataclass

@dataclass
class StoryConfig:
    azure_openai_key: str
    azure_openai_endpoint: str
    azure_api_version: str = "2024-12-01-preview"
    deployment_name: str = "gpt-5-chat"
