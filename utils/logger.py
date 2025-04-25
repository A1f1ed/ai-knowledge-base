import logging
import streamlit as st
from datetime import datetime
from pathlib import Path

# log directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# log format
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"
log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# initialize main logger
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("knowledge_base")

# output filter designed for Streamlit pages (only error/warning)
class StreamlitHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            st.error(msg)
        elif record.levelno >= logging.WARNING:
            st.warning(msg)
        # do not show info/debug level, to avoid UI interference

# add Streamlit handler (non-recursive)
streamlit_handler = StreamlitHandler()
streamlit_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(streamlit_handler)

__all__ = ['logger']