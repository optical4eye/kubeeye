#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version information module for managing project version information
"""

# Major version number
VERSION_MAJOR = 2
# Minor version number
VERSION_MINOR = 0
# Patch number
VERSION_PATCH = 0
# Version tag (e.g. 'alpha', 'beta', 'rc1', leave empty for official release)
VERSION_TAG = 'alpha'

# Full version number
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
if VERSION_TAG:
    VERSION = f"{VERSION}-{VERSION_TAG}"

# Application name
APP_NAME = "kubeeye"
# Application description
APP_DESCRIPTION = "Kubernetes cluster inspection tool"
# Application author
APP_AUTHOR = "pixiake"
# Application homepage
APP_URL = "https://github.com/kubesphere/kubeeye"

# Release date
RELEASE_DATE = "2025-06-25"

def get_version():
    """Get current version number"""
    return VERSION

# Version information dictionary
VERSION_INFO = {
    'name': APP_NAME,
    'version': VERSION,
    'description': APP_DESCRIPTION,
    'author': APP_AUTHOR,
    'url': APP_URL,
    'release_date': RELEASE_DATE
}

def get_version_info():
    """Get version information dictionary"""
    return VERSION_INFO

def get_version_string():
    """Get version string"""
    return f"{APP_NAME} v{VERSION}"

if __name__ == "__main__":
    print(get_version_string())
