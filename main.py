#!/usr/bin/env python3
"""
Quick test script for YouGen

Usage:
    python main.py auth              # Check authentication
    python main.py scan              # Scan tweets and generate comments
    python main.py review            # Review pending comments
    python main.py publish           # Publish approved comments
    python main.py stats             # Show statistics
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yougen.cli.main import main

if __name__ == '__main__':
    main()
