"""PyInstaller entry point — uses absolute imports."""
import sys
import os

# Ensure the package directory is on the path
if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    sys.path.insert(0, base)

from slide_viewer.app import main

main()
