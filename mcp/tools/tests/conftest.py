"""
Pytest Configuration für MCP Tool Tests.
"""

import sys
from pathlib import Path

# Add tools directory to path for imports
tools_path = Path(__file__).parent.parent
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path.parent))


# Shared fixtures können hier definiert werden
