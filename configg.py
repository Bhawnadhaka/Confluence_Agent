# config.py
import streamlit as st
import os
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()

def get_secret(key: str, default: Optional[Any] = None) -> Any:
    """
    Get configuration value from Streamlit secrets (cloud) 
    or environment variables (local development)
    
    Args:
        key: The configuration key to retrieve
        default: Default value if key not found (None raises error)
    
    Returns:
        The configuration value
        
    Raises:
        ValueError: If key not found and no default provided
    """
    try:
        # Try Streamlit secrets first (for cloud deployment)
        return st.secrets[key]
    except (KeyError, FileNotFoundError, RuntimeError, AttributeError):
        # Fall back to environment variables (for local dev)
        value = os.getenv(key, default)
        if value is None and default is None:
            raise ValueError(
                f"Missing required configuration: {key}\n"
                f"Please set it in .env file (local) or Streamlit secrets (cloud)"
            )
        return value