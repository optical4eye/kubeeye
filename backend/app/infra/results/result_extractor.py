#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core.logging import get_logger

"""
Result extractor module for extracting variables from command output
"""

import re
from typing import Dict, List, Any

# Configure logging
logger = get_logger(__name__)


class ResultExtractor:
    """Extracting variables from command output"""

    def extract(self, output: str, extractors: List[Dict], context: Dict = None) -> Dict[str, Any]:
        """
        Extract variables from output based on extractor configurations

        Args:
            output: Command output text
            extractors: List of extractor configurations
            context: Existing context variables

        Returns:
            Dictionary of extracted variables
        """
        result = context.copy() if context else {}

        for extractor in extractors:
            name = extractor.get("name")
            if not name:
                logger.warning("Extractor is missing the name field")
                continue

            pattern = extractor.get("pattern")
            value_type = extractor.get("type", "str")

            if pattern:
                # Use regular expressions for extraction
                try:
                    match = re.search(pattern, output)
                    if match:
                        # Check if there are capture groups
                        if match.groups():
                            # There are capture groups, use the first capture group
                            value = match.group(1)
                        else:
                            # No capture groups, use the entire match
                            value = match.group(0)
                        result[name] = self._convert_value(value, value_type)
                    else:
                        logger.warning(f"Extractor pattern '{name}' '{pattern}' found no matches")
                        result[name] = None
                except (re.error, IndexError) as e:
                    logger.error(f"Regex error for extractor '{name}': {str(e)}")
                    result[name] = None

        return result

    def _convert_value(self, value: str, value_type: str) -> Any:
        """
        Convert value type

        Args:
            value: String value
            value_type: Target type

        Returns:
            Converted value
        """
        try:
            if value_type == "int":
                return int(value)
            elif value_type == "float":
                return float(value)
            elif value_type == "bool":
                return value.lower() in ("true", "yes", "1", "on")
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert type: {str(e)}, returning original value")
            return value
