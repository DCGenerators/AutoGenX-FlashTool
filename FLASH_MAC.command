#!/bin/bash
cd "$(dirname "$0")" || exit 1
python3 autogen_flash.py
echo
echo "✅ Flash complete."
read -p "Press Enter to close..."
