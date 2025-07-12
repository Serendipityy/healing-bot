"""
Utility functions for Healing Bot frontend.
"""

from .api_client import APIClient, get_api_client, get_base64_of_image, format_conversation_title, set_background_image

__all__ = [
    "APIClient",
    "get_api_client",
    "get_base64_of_image",
    "format_conversation_title",
    "set_background_image"
]