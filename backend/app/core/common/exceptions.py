#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom exceptions for KubeEye
"""

from typing import Dict, Any, Optional


class KubeEyeException(Exception):
    """Base exception for KubeEye"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ClusterNotFoundError(KubeEyeException):
    """Raised when cluster configuration is not found"""

    pass


class InspectorError(KubeEyeException):
    """Raised when inspector execution fails"""

    pass


class RuleLoadError(KubeEyeException):
    """Raised when rule loading fails"""

    pass


class CommandSecurityError(KubeEyeException):
    """Raised when command fails security check"""

    pass


class ValidationError(KubeEyeException):
    """Raised when input validation fails"""

    pass


class GitOpsError(KubeEyeException):
    """Raised when GitOps operations fail"""

    pass


class DatabaseError(KubeEyeException):
    """Raised when database operations fail"""

    pass


class NetworkError(KubeEyeException):
    """Raised when network operations fail"""

    pass


class TaskNotFoundError(KubeEyeException):
    """Raised when scheduled task is not found"""

    pass


class InspectionError(KubeEyeException):
    """Raised when inspection operations fail"""

    pass


class PopeyeError(InspectorError):
    """Raised when Popeye inspector operations fail"""

    pass


class PopeyeBinaryNotFoundError(PopeyeError):
    """Raised when Popeye binary is not found"""

    pass


class PopeyeBinaryNotExecutableError(PopeyeError):
    """Raised when Popeye binary is not executable"""

    pass


class PopeyeTimeoutError(PopeyeError):
    """Raised when Popeye execution times out"""

    pass


class PopeyeExecutionError(PopeyeError):
    """Raised when Popeye execution fails"""

    pass


class PopeyeParseError(PopeyeError):
    """Raised when Popeye output parsing fails"""

    pass


class RepositoryError(DatabaseError):
    """Base exception for repository operations"""

    pass


class NotFoundError(RepositoryError):
    """Raised when entity is not found"""

    pass


class DuplicateError(RepositoryError):
    """Raised when attempting to create duplicate entity"""

    pass


class ConstraintError(RepositoryError):
    """Raised when database constraints are violated"""

    pass
