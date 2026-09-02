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

# F-12 运行依赖（首跑 CI 暴露的缺口）：backup_run / backup_restore 在
# web 容器内经 subprocess 调用 pg_dump / pg_restore（runbook §4–§6 的
# 正式用法），基础镜像 slim 不含 PG 客户端，须装与服务端 postgres:18
# 同大版本的客户端（PGDG 源按基础镜像 Debian 代号动态拼接；构建期网络
# 依赖仅此一层）。置于代码 COPY 之前，代码变更不使本层缓存失效。
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates; \
    install -d /usr/share/postgresql-common/pgdg; \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc; \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo "$VERSION_CODENAME")-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-client-18; \
    apt-get purge -y curl; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/*

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
    pip install --no-cache-dir --no-deps -e .; \
    useradd --create-home --shell /usr/sbin/nologin peiligo; \
    mkdir -p /data/media /data/static; \
    chown -R peiligo:peiligo /app /data

# 构建期 collectstatic（ManifestStaticFilesStorage 哈希清单固化进镜像）。
# 仅用哑值满足 settings 的快速失败（DATABASE_URL/SECRET_KEY/ALLOWED_HOSTS
# 均非真实秘密，运行时被真实环境变量覆盖）；本层不含任何运行期秘密。
ENV DJANGO_SETTINGS_MODULE=peiligo.settings.production \
    DATABASE_URL=postgres://build@localhost/build \
    SECRET_KEY=build-time-dummy-not-a-real-secret \
    ALLOWED_HOSTS=build.invalid \
    WAGTAILADMIN_BASE_URL=https://build.invalid
RUN python manage.py collectstatic --noinput

USER peiligo

EXPOSE 8000

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
# gunicorn＝冻结 WSGI 服务器（requirements 固定版本）；日志全走 stdout/
# stderr 由 docker 采集。GUNICORN_WORKERS 可经环境调参（缺省 2）。
CMD ["sh", "-c", "exec gunicorn peiligo.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-2} --timeout 60 --access-logfile - --error-logfile -"]
