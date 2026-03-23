"""
Slide Viewer — A Markdown-Powered Presentation Tool

Standalone desktop application for viewing and editing markdown-based slide decks.
Uses PyQt6 + QWebEngineView for rich rendering, with live editing, AI assistance,
and slide theme customization.
"""

from .app import main

__version__ = "1.0.0"
__all__ = ["main"]
