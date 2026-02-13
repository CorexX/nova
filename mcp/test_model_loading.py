#!/usr/bin/env python3
"""
Test-Skript für Background Model Loading.
Simuliert den MCP Server mit Threading.
"""

import sys
import time
import threading
import os

# Unterdrücke HuggingFace Progress-Bars
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Event für Model-Ready Status
model_ready = threading.Event()


def load_model_in_background():
    """Lädt das Model im Background-Thread."""
    print(f"[{time.strftime('%H:%M:%S')}] 🔄 Loading embedding model...", flush=True)
    
    start = time.time()
    try:
        # Unterdrücke ALLE Outputs während Model lädt
        import warnings
        import io
        import contextlib
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Capture stdout/stderr von HuggingFace/MLX
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                from tools.search.shared import get_model
                model = get_model()
        
        elapsed = time.time() - start
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Model ready ({elapsed:.1f}s)", flush=True)
        model_ready.set()
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed: {e}", flush=True)


def main():
    print(f"[{time.strftime('%H:%M:%S')}] 🚀 Starting...", flush=True)
    
    # Starte Background-Thread
    thread = threading.Thread(target=load_model_in_background, daemon=True)
    thread.start()
    
    print(f"[{time.strftime('%H:%M:%S')}] 📦 Main thread continues (not blocked)", flush=True)
    
    # Simuliere "Server läuft" - warte auf Model
    print(f"[{time.strftime('%H:%M:%S')}] ⏳ Waiting for model...", flush=True)
    
    if model_ready.wait(timeout=120):
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Model is ready! Can use search now.", flush=True)
    else:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Timeout waiting for model", flush=True)
    
    # Test: Model sollte gecached sein
    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Testing cached model...", flush=True)
    start = time.time()
    from tools.search.shared import get_model
    model = get_model()
    print(f"[{time.strftime('%H:%M:%S')}] ✅ Cached access: {time.time()-start:.3f}s", flush=True)


if __name__ == "__main__":
    main()
