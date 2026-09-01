# F-09：Peiligo V1 生产镜像（冻结栈 Python 3.13＋Django 5.2＋Wagtail 7.4，
# gunicorn WSGI；无 Node/前端构建——static/ 为纯 CSS/JS，collectstatic 直收）。
# 仓库布局：Django app 包（home/ 等）与 manage.py 同在仓库根，项目配置包
# 在 src/peiligo（经 pip editable 安装，与 venv 开发同构）。
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 依赖层先行（requirements 未变则缓存命中）。
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 代码层（多源 COPY 逐目录落位到 /app/；.dockerignore 排除 .env/.git/
# venv/测试产物/media 等非构建上下文）。
COPY manage.py pyproject.toml ./
COPY home/ notices/ departments/ guides/ resources/ search/ frontend/ locale/ ./
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/
COPY deploy/docker-entrypoint.sh ./deploy/docker-entrypoint.sh

# 运行身份：非 root；/data 为卷挂载点（media＋static，归属 peiligo，
# 命名卷首挂即继承该属主）。
RUN set -eux; \
    pip install --no-cache-dir --no-deps -e ./src; \
    useradd --create-home --shell /usr/sbin/nologin peiligo; \
    mkdir -p /data/media /data/static; \
    chown -R peiligo:peiligo /app /data

# 构建期 collectstatic（ManifestStaticFilesStorage 哈希清单固化进镜像）。
# 仅用哑值满足 settings 的快速失败（DATABASE_URL/SECRET_KEY/ALLOWED_HOSTS
# 均非真实秘密，运行时被真实环境变量覆盖）；本层不含任何运行期秘密。
ENV DJANGO_SETTINGS_MODULE=peiligo.settings.production \
    DATABASE_URL=postgres://build@localhost/build \
    SECRET_KEY=build-time-dummy-not-a-real-secret \
    ALLOWED_HOSTS=build.invalid
RUN python manage.py collectstatic --noinput

USER peiligo

EXPOSE 8000

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
# gunicorn＝冻结 WSGI 服务器（requirements 固定版本）；日志全走 stdout/
# stderr 由 docker 采集。GUNICORN_WORKERS 可经环境调参（缺省 2）。
CMD ["sh", "-c", "exec gunicorn peiligo.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-2} --timeout 60 --access-logfile - --error-logfile -"]
