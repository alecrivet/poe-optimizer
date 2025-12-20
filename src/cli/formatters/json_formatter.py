"""JSON output formatter."""

import json
from typing import Dict, Any, Optional
from pathlib import Path


class JsonFormatter:
    """Format output as JSON."""

    @staticmethod
    def format(data: Dict[str, Any], pretty: bool = True) -> str:
        """Format data as JSON string."""
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    @staticmethod
    def save(data: Dict[str, Any], path: str, pretty: bool = True):
        """Save data to JSON file."""
        json_str = JsonFormatter.format(data, pretty)
        Path(path).write_text(json_str)

    @staticmethod
    def load(path: str) -> Dict[str, Any]:
        """Load data from JSON file."""
        return json.loads(Path(path).read_text())
