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
