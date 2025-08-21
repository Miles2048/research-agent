#!/usr/bin/env python3
"""
Simple API server startup script
"""

import uvicorn
import os
import sys

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from api.main import app

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )