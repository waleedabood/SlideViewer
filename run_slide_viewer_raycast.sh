#!/usr/bin/env bash

# @raycast.schemaVersion 1
# @raycast.title Launch Slide Viewer
# @raycast.mode silent
# @raycast.packageName Slide Viewer
# @raycast.icon 🎞️

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"
python3 -m slide_viewer
