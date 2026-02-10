#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base controller with common validation and error handling logic
"""

from typing import TypeVar

from core.logging import get_logger
from core.common.unified_error_handler import (
    OperationExecutor,
    create_success_response,
    create_error_response,
    validate_and_sanitize_param,
)

logger = get_logger(__name__)
T = TypeVar("T")


class BaseController(OperationExecutor):
    """
    Base controller class providing common validation and error handling functionality

    Inherits from OperationExecutor to avoid code duplication.
    """

    def __init__(self):
        super().__init__(logger_instance=get_logger(self.__class__.__name__))

    # Re-export validate_and_sanitize_param from unified_error_handler for convenience
    validate_and_sanitize_param = staticmethod(validate_and_sanitize_param)

    # Re-export response creation functions from unified_error_handler for convenience
    create_success_response = staticmethod(create_success_response)
    create_error_response = staticmethod(create_error_response)
