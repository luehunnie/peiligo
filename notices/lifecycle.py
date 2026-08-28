"""内容生命周期状态机与发布窗口政策（CONTENT_MODEL §14/§16；M3.3 落地）。

- ``LifecycleStateMixin``：五状态只读推导（§14.2）——零新增字段，纯计算
  口径同 §7.1 ``event_status``（"落实为只读 property 与测试断言"）；
  仅混入 §1.2 五类内容页，结构页与受控数据不适用（§14.1）。
- ``clean_publish_window``：§16.1/§16.2 逐模型 expire_at 政策——落实层＝
  模型 ``clean()``（发布动作经 ``save_revision``/``publish`` 同一校验链，
  单一闸口）。
- ``current_default_pages``：§16.4 CURRENT_DEFAULT（前台当前有效集＝S2）
  查询集谓词，V1 全部前台位置消费此集；HISTORICAL/ARCHIVE-SEARCH 归
  M5.2（PS-26：落地前不得声称已提供历史归档查询）。
- M5.2（PUBLISH_ARCHIVE_SCHEDULING §6–§7）：``historical_pages``＝
  HISTORICAL 集（S2 ∪ S3）谓词，消费位＝板块历史归档视图与搜索入口
  （ARCHIVE-SEARCH 同谓词，§7.1 状态中性口径）；``route`` 覆写＝§6.3
  载体①（expired 页具名 URL 放行渲染，差异登记见 CONTENT_MODEL §16.4）。
"""

from django.db.models import Q
from django.utils import timezone
from wagtail.models import Page
from wagtail.url_routing import RouteResult

# §14.2 五状态常量（推导值，不落库；编号 S0–S4 见设计表）。
LIFECYCLE_DRAFT = "draft"  # S0 草稿（从未发布）
LIFECYCLE_SCHEDULED = "scheduled"  # S1 预约发布中
LIFECYCLE_LIVE = "live"  # S2 已发布（在线）
LIFECYCLE_EXPIRED = "expired"  # S3 已到期
LIFECYCLE_UNPUBLISHED = "unpublished"  # S4 已下线

# §16.4/§7 可见性口径常量（M5.2）：搜索/列表共用过滤层（§21.1）按入口
# 绑定谓词（§7 补充口径）——板块默认列表入口＝CURRENT_DEFAULT，/search/
# 搜索入口与板块归档视图＝HISTORICAL（ARCHIVE-SEARCH 与 HISTORICAL 同
# 谓词 ``Q(live) ∪ Q(expired)``，仅消费位不同，§6.1/§7.1 同口径）。
VISIBILITY_CURRENT_DEFAULT = "current_default"
VISIBILITY_HISTORICAL = "historical"


class LifecycleStateMixin:
    """五状态推导 Mixin（§14.2，只读 property、零存储字段）。

    消费方：五类内容页（§1.2）与 FeaturedItem 展示有效性（§15.4）。
    状态仅经 E1–E11 转换变更；编辑保存修订不改变状态（§14.3 正交声明）。
    """

    @property
    def lifecycle_state(self):
        """五状态（§14.2 表，优先级自上而下、先命中先得）。

        - S2 先于一切：live 页恒为 S2（子态 S2a/S2b＝``has_unpublished_changes``
          直读内建列）；live 页带未来 expire_at 属 S2 属性，不单设状态。
        - S1 挂钩修订级 ``Revision.approved_go_live_at`` 待执行修订（官方
          ``scheduled_revision`` 同源谓词）；对象级 ``go_live_at`` 残留不参与
          判定（§14.2 注记：E3/E7/E8 均不清对象级，残留＋expired/unpublished
          须仍判 S3/S4）。
        - live=T ∧ expired=T 经 E7 原子置位不可达；对合法数据总可判定，
          非法组合返回 None。
        """
        if self.live and not self.expired:
            return LIFECYCLE_LIVE
        if not self.live:
            if self.scheduled_revision is not None:
                return LIFECYCLE_SCHEDULED
            if self.expired:
                return LIFECYCLE_EXPIRED
            if self.first_published_at is not None:
                return LIFECYCLE_UNPUBLISHED
            return LIFECYCLE_DRAFT
        return None

    @property
    def in_current_default(self):
        """§16.4 CURRENT_DEFAULT 成员判定（状态 ∈ {S2} 即前台当前有效集）。"""
        return self.lifecycle_state == LIFECYCLE_LIVE

    def route(self, request, path_components):
        """§6.3 载体①（M5.2）：expired 页具名 URL 放行渲染。

        Wagtail 叶子路由判定仅认 ``live``（live=F → Http404）；本覆写对
        S3（expired）返回本页，使「经归档视图或搜索结果到达的 expired
        条目正文可读」的 §6.3 语义不变式成立（页首「已过期」横幅由模板
        承载）。S0/S1/S4 落回内建判定＝404（§7 总表末行不变）；五类内
        容页经本 Mixin 统一获得该行为，容器/结构页未混入、维持内建
        （容器恒 404，IA §3.2）。与 §16.4 CURRENT_DEFAULT 行「非本集具名
        URL＝404」的字面差异按 §6.3-4 义务登记于 CONTENT_MODEL §16.4。
        """
        if not path_components and self.expired:
            return RouteResult(self)
        return super().route(request, path_components)


# §16.1 逐模型 expire_at 政策（冻结表：Notice 必填＋未来／Article 可选须
# 未来／Material·SoftwareTool·Guide clean 强制空）。
EXPIRE_REQUIRED = "required"
EXPIRE_OPTIONAL = "optional"
EXPIRE_FORBIDDEN = "forbidden"


def clean_publish_window(page, errors, policy):
    """发布窗口政策 clean（§16.1/§16.2；就地向 ``errors`` 填充）。

    防三类无效配置：通知发布即已过期（§16.2 未来性）；文章如填写到期则
    不得为过去（§16.2）；常青内容误配到期致静默消失（§16.1 强制空——其
    退场方式＝E8 手动下线，PRD §8）。E9/E10/E11 重发布/重预约经同一
    clean 自然强制新有效期（§16.2 落实层说明）。

    M5.1（§5.4/PA-12）扩展：``go_live_at`` 与 ``expire_at`` 同时非空时须
    ``go_live_at < expire_at``（严于官方 admin 表单"仅拒 ``>``、相等放行"，
    封死经相等路径可达的"上线即已过期"窗口）。官方校验仅覆盖表单路径，
    本 clean 是全路径闸口（脚本/API/后台定制同经此校验）。
    """
    expire_at = page.expire_at
    if policy == EXPIRE_FORBIDDEN:
        if expire_at is not None:
            errors["expire_at"] = ["该内容类型不设有效期，到期时间须留空（CONTENT_MODEL §16.1）"]
        return
    if policy == EXPIRE_REQUIRED and not expire_at:
        errors["expire_at"] = ["通知必须填写有效期（CONTENT_MODEL §5.2/CM-01）"]
        return
    if expire_at is not None and expire_at <= timezone.now():
        errors["expire_at"] = ["有效期必须晚于当前时刻（CONTENT_MODEL §16.2）"]
    go_live_at = page.go_live_at
    if go_live_at is not None and expire_at is not None and go_live_at >= expire_at:
        errors["go_live_at"] = ["预约发布时间必须早于到期时间（PUBLISH_ARCHIVE_SCHEDULING §5.4）"]


def current_default_pages():
    """§16.4 CURRENT_DEFAULT 查询集：状态 ∈ {S2} 的页面。

    ``expired=False`` 合取按定义显式声明（expired ⇒ live=F 时本冗余，但
    使谓词自含 §14.2 S2 全条件）；draft/scheduled/unpublished/expired
    一律不在集内（PS-25）。V1 前台全部位置（路由 404 内建、板块默认
    列表、搜索 live 基线）消费此集；HISTORICAL/ARCHIVE-SEARCH 是 M5.2
    契约，本仓库落地前不得声称已提供历史归档查询（PS-26）。
    """
    return Page.objects.live().filter(expired=False)


def historical_pages():
    """§16.4 HISTORICAL 查询集：状态 ∈ {S2, S3} 的页面（M5.2 §6.1）。

    实现谓词＝``Q(live=True) | Q(expired=True)``——``live ∧ expired`` 经
    E7 原子置位不可达（§14.2 注），合取互斥故并集恰为 S2 ∪ S3。消费位＝
    五板块历史归档视图（§6.1）与 expired 具名 URL 放行（§6.3 载体①）；
    S0/S1/S4 恒不在集（PS-25）。与 ``current_default_pages`` 同源扩展
    （§6.2-2），零新增状态字段（PA-23）。
    """
    return Page.objects.filter(Q(live=True) | Q(expired=True))
