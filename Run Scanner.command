#!/bin/bash
cd "$(dirname "$0")"
echo "============================================"
echo "  Weekes AATF — Running Earnings Scanner"
echo "============================================"
echo ""
python3 main.py --check-only
echo ""
echo "Done. Press any key to close."
read -n 1
