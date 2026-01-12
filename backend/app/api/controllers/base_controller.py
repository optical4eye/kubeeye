#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base controller with common validation and error handling logic
"""

from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable
from fastapi import HTTPException

from core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


class BaseController:
    """Base controller class providing common validation and error handling functionality"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def execute_operation(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
        success_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> T:
        """
        Execute an operation with standardized error handling and logging

        Args:
            operation: Async callable to execute
            operation_name: Name of the operation for logging
            success_message: Optional success message to log
            error_message: Optional error message prefix

        Returns:
            Result of the operation

        Raises:
            HTTPException: For errors during operation
        """
        try:
            self.logger.info(f"Starting {operation_name}")

            result = await operation()

            if success_message:
                self.logger.info(success_message)
            else:
                self.logger.info(f"{operation_name} completed successfully")

            return result

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            # Convert ValueError to HTTP 400
            error_msg = f"{error_message or operation_name} validation error: {str(e)}"
            self.logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Convert other exceptions to HTTP 500
            error_msg = f"{error_message or operation_name} error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)

    def execute_sync_operation(
        self,
        operation: Callable[[], T],
        operation_name: str,
        success_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> T:
        """
        Execute a synchronous operation with standardized error handling and logging

        Args:
            operation: Callable to execute
            operation_name: Name of the operation for logging
            success_message: Optional success message to log
            error_message: Optional error message prefix

        Returns:
            Result of the operation

        Raises:
            HTTPException: For errors during operation
        """
        try:
            self.logger.info(f"Starting {operation_name}")

            result = operation()

            if success_message:
                self.logger.info(success_message)
            else:
                self.logger.info(f"{operation_name} completed successfully")

            return result

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            # Convert ValueError to HTTP 400
            error_msg = f"{error_message or operation_name} validation error: {str(e)}"
            self.logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Convert other exceptions to HTTP 500
            error_msg = f"{error_message or operation_name} error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)

    def validate_and_sanitize_param(
        self, param_value: Any, param_name: str, validator: Optional[Callable[[Any], Any]] = None, required: bool = True
    ) -> Any:
        """
        Validate and sanitize a parameter

        Args:
            param_value: Parameter value to validate
            param_name: Name of the parameter for error messages
            validator: Optional validation function
            required: Whether the parameter is required

        Returns:
            Validated and sanitized parameter value

        Raises:
            HTTPException: If validation fails
        """
        if required and (param_value is None or param_value == ""):
            raise HTTPException(status_code=400, detail=f"Missing required parameter: {param_name}")

        if param_value is not None and validator:
            try:
                return validator(param_value)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid {param_name}: {str(e)}")

        return param_value

    def create_success_response(self, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a standardized success response

        Args:
            message: Success message
            data: Optional additional data

        Returns:
            Response dictionary
        """
        response = {"message": message}
        if data:
            response.update(data)
        return response

    def create_error_response(
        self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized error response

        Args:
            error_type: Type of error
            message: Error message
            details: Optional error details

        Returns:
            Response dictionary
        """
        response = {"error": error_type, "message": message}
        if details:
            response.update(details)
        return response
