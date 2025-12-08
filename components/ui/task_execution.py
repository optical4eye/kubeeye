#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task execution component - refactored version, using unified inspection engine
"""
from components.ui.inspection_engine import execute_inspection_task

# Directly export execute_inspection_task function to maintain backward compatibility
__all__ = ['execute_inspection_task']
