"""
Shared resources for Search Tools.
Cached embedding model to avoid reloading on every call.
"""
import os
import warnings
import logging

# Suppress HuggingFace/transformers warnings
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*resume_download.*")

# Suppress library loggers
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

_model = None
_chromadb = None

def get_model():
    """Returns cached SentenceTransformer model. Loads once, then reuses."""
    global _model
    if _model is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def get_chromadb():
    """Returns cached chromadb module."""
    global _chromadb
    if _chromadb is None:
        import chromadb as _chromadb_module
        _chromadb = _chromadb_module
    return _chromadb
