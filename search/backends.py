"""F-01 · E1 搜索后端显式选择（ADR-0006 · 中文搜索后端，Accepted 2026-08-31）。

生产库为 PostgreSQL，通用 ``wagtail.search.backends.database`` 按连接
vendor 分派——PG 连接走 FTS 路径＝E2 语义，icontains fallback 不可达
（ADR-0006 §背景/§决策：PRODUCTION_IMPLEMENTATION_REQUIRED=YES）。
本模块即 ADR-0006 点名的「显式选择 fallback/DatabaseSearchBackend」：
``default`` 后端固定为 DB fallback 实现，任何数据库 vendor 下均为
icontains 子串语义，不再发生 vendor 分派。

边界（随 E1 选型带入的已接受结构性差异，CM §20.2）：

- 仅顶层 SearchField 进检索文本（title/summary/body 及各页自有结构化
  字段）；RelatedFields 文本（部门名/标签名/学科词表名等）缺席；
- boost 被忽略；无相关度排序，结果保 ``-first_published_at`` 序
  （services 层保序旋钮统一施加）。

不改 Wagtail/modelsearch 核心；语义锁定回归见
``tests/test_search_e1_backend.py``，金标集功能回归见
``tests/test_search_golden_set.py``。
"""

from wagtail.search.backends.database.fallback import DatabaseSearchBackend


class E1IcontainsSearchBackend(DatabaseSearchBackend):
    """E1：Wagtail DB 后端 icontains fallback，固定用于任何数据库 vendor。"""
