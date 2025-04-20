#!/bin/bash
uv sync
source .venv/bin/activate

cd /home/ubuntu/MengLong/
uv pip install -e .