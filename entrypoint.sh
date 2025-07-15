#!/bin/sh

# 初始化数据库
echo "Initializing the database..."
python -m app.cli init-db-command

# Start Uvicorn server
echo "Starting Uvicorn server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000