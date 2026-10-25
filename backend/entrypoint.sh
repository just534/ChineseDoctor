#!/bin/sh
set -e
# 数据库迁移（幂等）
alembic upgrade head
# 初始化权限/角色/管理员并导入内容（只执行一次，避免多 worker 并发初始化）
python -m app.cli init
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w "${WEB_CONCURRENCY:-2}" \
  -b 0.0.0.0:8000 \
  --forwarded-allow-ips="*" \
  --timeout 120 \
  --access-logfile -
