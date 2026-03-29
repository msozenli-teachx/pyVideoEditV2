"""
Zed Operations Module

Media operations that use the FFmpeg engine.
Provides extensible operation handlers for video editing.
"""

from .clip import VideoClipper

__all__ = ['VideoClipper']
