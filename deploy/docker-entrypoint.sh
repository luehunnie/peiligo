#!/bin/sh
# F-09：web 容器入口——等库、迁移、静态文件落卷，再交给 gunicorn。
# 单机 compose 形态下迁移由 web 容器串行执行一次（幂等，--noinput）；
# scheduler 容器经 compose depends_on(web healthy) 保证在迁移完成后启动。
set -eu

echo "[entrypoint] waiting for database ..."
until python manage.py check --database default >/dev/null 2>&1; do
  sleep 1
done

echo "[entrypoint] applying migrations ..."
python manage.py migrate --noinput

echo "[entrypoint] publishing static files to shared volume ..."
cp -a /app/staticfiles/. /data/static/

echo "[entrypoint] starting: $*"
exec "$@"
