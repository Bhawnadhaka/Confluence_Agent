import logging
from summarizer.summarizer_core import SummarizerCore

def run_summarizer(figma_preprocessed_data: dict) -> dict:
   
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger(__name__)

    if not isinstance(figma_preprocessed_data, dict):
        raise ValueError("Expected preprocessed Figma data as dict.")

    log.info(" Running Figma summarizer...")

    summarizer = SummarizerCore(figma_data=figma_preprocessed_data)
    summarized_data = summarizer.run()

    log.info(" Summarization completed successfully.")
    return summarized_data
