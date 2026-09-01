"""F-07（SB §6.2 / 结构化 LOGGING）：单行 JSON 日志格式化器。

稳定字段（JSON 兼容，供采集器/检索按名取用）：
- ``ts``：ISO-8601 UTC 绝对时刻；
- ``level``：logging 级别名；
- ``logger``：记录器名；
- ``event``：稳定事件码（接收方经 ``extra={"event": "auth.login"}`` 传入；
  缺省时 ≥ERROR 记 ``app.error``，其余 ``app.log``）；
- ``msg``：人读消息；
- 其余 ``extra`` 项经敏感键清洗后平铺为顶层字段；
- 有异常时 ``exc``：``{"type", "value", "stack"}``（堆栈仅入日志管道，
  不经 HTTP 响应外泄——与 F-02 口径分层）。

脱敏规则＝SB §6.2 落地：
1. 不记录密码/密钥/env 值/Token——敏感键命中即整键丢弃（纵深防御层；
   首要纪律是事件发射处只传明确白名单小字典，不做请求体/环境变量整体倾倒）；
2. 附件内容不入日志（事件只携元数据：文件名等）；
3. 用户身份仅岗位账号名（username），不记姓名；
4. DEBUG 级不入生产管道——LOGGING 各 logger 层级 ≥INFO 收敛（settings）。
"""

import json
import logging
import sys
import traceback
from datetime import UTC, datetime

# 敏感键清洗名单（SB §6.2 #1）：extra 键名不区分大小写命中即弃。
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secret_key",
        "token",
        "api_key",
        "authorization",
        "cookie",
        "session",
        "env",
        "environ",
    }
)

# 稳定骨架字段（不参与清洗，由本格式化器自产）。
STABLE_FIELDS = ("ts", "level", "logger", "event", "msg")


def scrub_extra(extra):
    """按 SENSITIVE_KEYS 清洗 extra 字典（返回新字典，键转小写比对）。"""
    return {key: value for key, value in extra.items() if key.lower() not in SENSITIVE_KEYS}


class JsonFormatter(logging.Formatter):
    """logging.Formatter：单行 JSON 输出（ stdout/stderr 采集友好）。"""

    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None)
            or ("app.error" if record.levelno >= logging.ERROR else "app.log"),
            "msg": record.getMessage(),
        }
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in STABLE_FIELDS
            and key
            not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "stack",
                "taskName",
                "thread",
                "threadName",
            )
        }
        payload.update(scrub_extra(extra))
        if record.exc_info:
            # Python ≥3.13 在记录构造期不再展开 exc_info=True（保持布尔惰性
            # 形态），格式化时自行归一化。
            exc_info = record.exc_info
            if not isinstance(exc_info, tuple):
                if isinstance(exc_info, BaseException):
                    exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
                else:
                    exc_info = sys.exc_info()
            exc_type, exc_value, exc_tb = exc_info
            payload["exc"] = {
                "type": exc_type.__name__ if exc_type is not None else None,
                "value": str(exc_value) if exc_value is not None else None,
                "stack": "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            }
        return json.dumps(payload, ensure_ascii=False, default=str)
