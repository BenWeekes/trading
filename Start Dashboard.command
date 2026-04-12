#!/bin/bash
cd "$(dirname "$0")"
echo "============================================"
echo "  Weekes AATF — Starting Dashboard"
echo "============================================"
echo ""
echo "Starting server at http://localhost:5050"
echo "Press Ctrl+C to stop."
echo ""
python3 dashboard_server.py
