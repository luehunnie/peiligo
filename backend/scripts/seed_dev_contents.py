"""开发演示数据 seed：仅向本地 peiligo_dev 的 contents 表写入虚构内容。

严格安全限制（任一不符即拒绝执行）：
- host 仅允许 localhost / 127.0.0.1
- database 仅允许 peiligo_dev
- username 仅允许 peiligo_dev_user
- contents 表已有任意数据时立即停止：不覆盖、不删除、不 truncate、不提供清空逻辑

本脚本不修改 schema / migration / API 契约，不创建管理员。
所有内容均为虚构演示数据，不含任何真实学生信息或真实校园公告。
"""

import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

from sqlalchemy import func, select

from app.config import DATABASE_URL
from app.database import SessionLocal
from app.models.content import Content


def _assert_safe_target(database_url: str) -> None:
    """解析 DATABASE_URL，严格校验连接目标仅限本地 dev 环境。"""
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    database = (parsed.path or "").lstrip("/")
    username = unquote(parsed.username or "")

    problems: list[str] = []
    if host not in ("localhost", "127.0.0.1"):
        problems.append(f"host={host!r}（仅允许 localhost / 127.0.0.1）")
    if database != "peiligo_dev":
        problems.append(f"database={database!r}（仅允许 peiligo_dev）")
    if username != "peiligo_dev_user":
        problems.append(f"username={username!r}（仅允许 peiligo_dev_user）")

    if problems:
        print("拒绝执行：连接目标不符合本地 dev 安全要求：")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)


# 固定时区，避免依赖运行机器时区，保证 published_at 合理且可复现
_TZ = timezone(timedelta(hours=8))


def _build_seed_rows() -> list[Content]:
    """构造虚构演示数据：五个板块各至少 1 条 published，另含 1 draft / 1 offline。"""
    # 五条 published，覆盖全部 content_type；body 多段以验证段落拆分
    published_base = datetime(2025, 3, 1, 9, 0, 0, tzinfo=_TZ)

    rows: list[Content] = [
        Content(
            content_type="campus-story",
            title="春日校园随手记：图书馆窗边的一束光",
            summary="一组虚构的校园生活随笔片段，展示多段落正文与图片字段演示。",
            body=(
                "清晨的图书馆总是安静得能听见翻页声。\n"
                "\n"
                "阳光斜斜地穿过落地窗，在桌面上铺开一片暖色，像是给每一本书都镀上了金边。\n"
                "\n"
                "有人戴着耳机专注地写着什么，有人在书架间来回踱步。这大概就是校园里最普通、也最让人安心的画面之一。"
            ),
            source_name=None,
            source_url=None,
            extra_data={
                "author_label": "校园观察员",
                "reading_minutes": 4,
                "featured": True,
                "tags": ["校园生活", "随笔"],
            },
            status="published",
            published_at=published_base,
        ),
        Content(
            content_type="campus-activity",
            title="春季社团开放日（虚构演示）",
            summary="一个用于演示的活动条目，含场地、容量与标签等结构化字段。",
            body=(
                "本条目为演示数据，并不对应任何真实活动安排。\n"
                "\n"
                "示例正文用于验证多段落渲染：第一段介绍活动概况，第二段说明参与方式。\n"
                "\n"
                "所有时间、地点、人数均为虚构，仅用于前端界面联调。"
            ),
            source_name="校园社团联合会（虚构）",
            source_url="https://example.com/activities/spring-fair",
            extra_data={
                "location": "校园北广场",
                "capacity": 120,
                "free_entry": True,
                "tags": ["社团", "周末"],
            },
            status="published",
            published_at=published_base - timedelta(days=2),
        ),
        Content(
            content_type="learning-resource",
            title="高等数学复习提纲（示例演示版）",
            summary="虚构的学习资料条目，展示学科、难度、预估时长等结构化字段。",
            body=(
                "这是一份用于演示的学习资料条目，内容全部虚构。\n"
                "\n"
                "提纲按章节组织，包含基础概念回顾与典型例题，便于验证资料类卡片的展示。\n"
                "\n"
                "请勿将其视为真实学习建议，所有数值仅为演示。"
            ),
            source_name="学习资源组（虚构）",
            source_url=None,
            extra_data={
                "subject": "高等数学",
                "difficulty": "中级",
                "estimated_hours": 8.5,
                "formats": ["PDF", "在线"],
            },
            status="published",
            published_at=published_base - timedelta(days=4),
        ),
        Content(
            content_type="software-resource",
            title="跨平台笔记工具（演示）",
            summary="虚构的软件资源条目，展示平台列表、版本、体积等字段。",
            body=(
                "该条目为演示用途，不代表任何真实软件。\n"
                "\n"
                "正文分多段：先描述功能定位，再说明支持的操作系统。\n"
                "\n"
                "所有版本号、体积数据均为虚构，仅用于界面联调。"
            ),
            source_name="校园软件镜像（虚构）",
            source_url="https://example.com/software/note-tool",
            extra_data={
                "platforms": ["Windows", "macOS"],
                "version": "1.2.0",
                "free": True,
                "size_mb": 256,
            },
            status="published",
            published_at=published_base - timedelta(days=6),
        ),
        Content(
            content_type="college-guide",
            title="升学规划起步指南（示例）",
            summary="虚构的升学指导条目，展示适用年级、地区与标签字段。",
            body=(
                "本指南为演示数据，不构成任何真实升学建议。\n"
                "\n"
                "正文以多段方式呈现：先给出总体思路，再拆分阶段目标。\n"
                "\n"
                "所有年级、地区信息均为示例，请勿据此做实际决策。"
            ),
            source_name=None,
            source_url=None,
            extra_data={
                "applicable_grade": 12,
                "region": "国内升学",
                "tags": ["志愿", "规划"],
                "priority": True,
            },
            status="published",
            published_at=published_base - timedelta(days=8),
        ),
        # 额外 1 条 draft：不在公开列表，用于验证详情 404
        Content(
            content_type="learning-resource",
            title="草稿示例：未发布的资料（演示）",
            summary="用于演示 draft 状态：不出现在公开列表，详情接口应返回 404。",
            body=(
                "这是一条草稿演示数据。\n"
                "\n"
                "由于状态为 draft，公开 API 不会返回它。"
            ),
            source_name=None,
            source_url=None,
            extra_data={"subject": "演示学科", "draft_note": True},
            status="draft",
            published_at=None,
        ),
        # 额外 1 条 offline：曾在发布后下线，同样不在公开列表
        Content(
            content_type="campus-story",
            title="已下线示例：一条失效的校园故事（演示）",
            summary="用于演示 offline 状态：不出现在公开列表，详情接口应返回 404。",
            body=(
                "这是一条已下线的演示数据。\n"
                "\n"
                "状态为 offline，公开 API 不会返回它。"
            ),
            source_name=None,
            source_url=None,
            extra_data={"tags": ["已下线"], "archived": True},
            status="offline",
            published_at=published_base - timedelta(days=30),
        ),
    ]
    return rows


def main() -> None:
    # 1) 写入前先校验连接目标，避免误连 test / 生产 / 未知库
    _assert_safe_target(DATABASE_URL)

    session = SessionLocal()
    try:
        # 2) contents 已有任意数据则立即停止，绝不覆盖或清空
        existing = session.execute(select(func.count()).select_from(Content)).scalar_one()
        if existing > 0:
            print(f"停止：contents 表已有 {existing} 条数据，拒绝覆盖或清空。")
            sys.exit(1)

        rows = _build_seed_rows()
        session.add_all(rows)
        session.commit()

        print(f"已插入 {len(rows)} 条虚构演示数据。")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
