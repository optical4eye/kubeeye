#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main API entry point - imports from routes modules
"""

from routes.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
