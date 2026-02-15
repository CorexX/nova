#!/usr/bin/env python3
"""
Standalone encoder worker.
Runs in a subprocess to avoid PyTorch/MCP conflicts on Windows.

Usage:
    python encoder_worker.py encode "query text"
    python encoder_worker.py batch_encode < texts.json
"""
import sys
import json
import os

# Suppress warnings
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*resume_download.*")

import logging
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: encoder_worker.py encode|batch_encode [text]"}))
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    if cmd == "encode":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "encode requires text argument"}))
            sys.exit(1)
        text = sys.argv[2]
        embedding = model.encode(text).tolist()
        print(json.dumps({"embedding": embedding}))
    
    elif cmd == "batch_encode":
        # Read JSON array of texts from stdin
        texts = json.load(sys.stdin)
        embeddings = model.encode(texts).tolist()
        print(json.dumps({"embeddings": embeddings}))
    
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
