#!/bin/sh
# F-09：web 容器入口——等库、迁移、静态文件落卷，再交给 gunicorn。
# 单机 compose 形态下迁移由 web 容器串行执行一次（幂等，--noinput）；
# scheduler 容器经 compose depends_on(web healthy) 保证在迁移完成后启动。
set -eu

echo "[entrypoint] waiting for database ..."
# 独立审查 P2 修复：`manage.py check --database` 对不可达数据库也退出 0
# （配置层校验，不做真实连接），不能作等库探针；此处改为经 Django
# 连接层实连一次（SELECT 级连通性），失败即重试。
until python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'peiligo.settings.production')
import django
django.setup()
from django.db import connection
connection.ensure_connection()
" >/dev/null 2>&1; do
  sleep 1
done

echo "[entrypoint] applying migrations ..."
python manage.py migrate --noinput

echo "[entrypoint] publishing static files to shared volume ..."
cp -a /app/staticfiles/. /data/static/

echo "[entrypoint] starting: $*"
exec "$@"
