# modules/story_generator/run_story_generator.py
import logging
from configg import get_secret

from .config import StoryConfig
from .confluence_agent import ConfluenceAgent
from .generator_core import ConfluenceStoryGenerator

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_story_generation(clickup_processed, summarized_figma, base_path=None):
    """Generate story using Azure OpenAI (works for local and cloud)"""
    
    config = StoryConfig(
        azure_openai_key=get_secret("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=get_secret("AZURE_OPENAI_ENDPOINT"),
        deployment_name=get_secret("AZURE_OPENAI_MODEL", "gpt-4o")
    )

    story_generator = ConfluenceStoryGenerator(config)
    agent = ConfluenceAgent(story_generator, base_path=base_path)

    doc = agent.generate_complete_story(
        clickup_data=clickup_processed,
        figma_data=summarized_figma
    )

    return agent.save_story_to_file(doc)