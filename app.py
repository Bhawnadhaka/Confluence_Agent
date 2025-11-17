# app.py
import os 
import streamlit as st
import time
from pathlib import Path
from dotenv import load_dotenv  # 👈 add this

# ---- Load environment ----
load_dotenv()
CLICKUP_TOKEN = os.getenv("CLICKUP_API_TOKEN")
FIGMA_TOKEN = os.getenv("FIGMA_TOKEN")

# ---- Import your project modules ----
from clickup_extractor import ClickUpTaskExtractor
from figma_extractor import FigmaPrototypeAnalyzer
from data_preprocessor import Preprocessor
from summarizer.run_summarizer import run_summarizer
from story_generator.run_story_generator import run_story_generation

# ---- Streamlit Page Config ----
st.set_page_config(
    page_title="Confluence Story Generator",
    page_icon="",
    layout="centered",
)

# ---- Custom CSS for beauty ----
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(to bottom right, #f5f7fa, #c3cfe2);
        font-family: "Segoe UI", sans-serif;
    }
    .title-text {
        text-align: center;
        font-size: 36px;
        color: #2b3e50;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .sub-text {
        text-align: center;
        color: #5a5a5a;
        font-size: 16px;
        margin-bottom: 30px;
    }
    .footer {
        text-align: center;
        color: #888;
        font-size: 12px;
        margin-top: 60px;
    }
</style>
""", unsafe_allow_html=True)

# ---- Header ----
st.markdown('<div class="title-text"> Confluence Story Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Fetch. Process. Summarize. Generate Word Story – Automatically.</div>', unsafe_allow_html=True)

# ---- Input Fields ----
st.markdown("### Enter Required Details")

col1, col2, col3 = st.columns(3)
with col1:
    clickup_task_id = st.text_input("🔹 ClickUp Task ID", placeholder="e.g., 2xhz45a")

with col2:
    figma_file_key = st.text_input("🔹 Figma File Key", placeholder="e.g., WPOfKpvJOgFbWQ1PX6U8sQ")

with col3:
    figma_node_id = st.text_input("🔹 Figma Node ID", placeholder="e.g., 1677:9265")

# ---- Button ----
st.markdown("---")
generate_btn = st.button(" Generate Story", use_container_width=True)

# ---- Backend Logic ----
if generate_btn:
    if not (clickup_task_id and figma_file_key and figma_node_id):
        st.error(" Please fill in all three fields before proceeding.")
    else:
        with st.spinner(" Fetching data from ClickUp and Figma... Please wait."):
            # Step 1: Fetch data from ClickUp and Figma
            clickup_extractor = ClickUpTaskExtractor(CLICKUP_TOKEN)
            clickup_data = clickup_extractor.fetch_task_enhanced(clickup_task_id)

            figma_extractor = FigmaPrototypeAnalyzer(FIGMA_TOKEN, figma_file_key, figma_node_id)
            figma_data = figma_extractor.run_extraction()  
            time.sleep(1)

        with st.spinner(" Preprocessing data..."):
            preprocessor = Preprocessor(clickup_data, figma_data, save_clickup=False)
            processed_data = preprocessor.run_all()
            preprocessed_clickup = processed_data["clickup_processed"]
            preprocessed_figma = processed_data["figma_processed"]
            
            time.sleep(1)


        with st.spinner(" Summarizing Figma Screens..."):
            summarized_figma_data = run_summarizer(preprocessed_figma)
            time.sleep(1)

        with st.spinner(" Generating Confluence Story Document..."):
            output_file = run_story_generation(preprocessed_clickup, summarized_figma_data)
            time.sleep(1)

        st.success(" Story generated successfully!")
        st.download_button(
            label="📥 Download Generated DOCX",
            data=open(output_file, "rb").read(),
            file_name=Path(output_file).name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

st.markdown('<div class="footer">Built with ❤️ using Streamlit and GPT-5</div>', unsafe_allow_html=True)
