# modules/story_generator/run_story_generator.py

import os
import logging
from dotenv import load_dotenv

from .config import StoryConfig
from .confluence_agent import ConfluenceAgent
from .generator_core import ConfluenceStoryGenerator

from summarizer.run_summarizer import run_summarizer


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_story_generation(clickup_processed, summarized_figma, base_path=None):
    load_dotenv()

    config = StoryConfig(
        azure_openai_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
    )

    story_generator = ConfluenceStoryGenerator(config)
    agent = ConfluenceAgent(story_generator, base_path=base_path)

    doc = agent.generate_complete_story(
        clickup_data=clickup_processed,
        figma_data=summarized_figma
    )

    return agent.save_story_to_file(doc)
