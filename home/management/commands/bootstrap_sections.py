"""五板块 bootstrap（M2.1 结构实现）：安全、幂等、零假业务内容。

在既有 HomePage（默认站点根，M1 迁移产物，不重建）下创建五个一级板块页：
中文名与 slug 冻结自 IA §2/§4.3（``home.models.SECTIONS`` 单一事实源）。

- 幂等：按「首页下同 slug 子页已存在」判定跳过，重复执行零副作用、零删除、
  零重复；已存在页的标题等编辑态不做任何改动。
- 安全：默认站点根不是 HomePage 时报错退出；同 slug 但非 SectionPage 的既有
  页仅告警跳过，不触碰。
- 零假业务内容：仅创建五个板块结构页（直接发布使前台 /<slug>/ 200）；
  不创建任何部门容器（建容器规则 IA §1.3：仅为确有内容的部门建容器，
  部门数据 M3 才有）、不写入任何业务数据。

用法：python manage.py bootstrap_sections
"""

from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Site

from home.models import SECTIONS, HomePage, SectionPage


class Command(BaseCommand):
    help = "在既有首页下幂等创建五个一级板块页（IA §2 冻结清单，零业务内容）"

    def handle(self, *args, **options):
        try:
            root = Site.objects.get(is_default_site=True).root_page.specific
        except Site.DoesNotExist as err:
            raise CommandError("未找到默认站点：请先运行 migrate 建立 M1 基线数据。") from err
        if not isinstance(root, HomePage):
            raise CommandError(
                f"默认站点根不是 HomePage 而是 {type(root).__name__}："
                "拒绝操作（复用现有首页，IA §1.1）。"
            )

        created = skipped = 0
        for section in SECTIONS:
            title, slug = section["title"], section["slug"]
            existing = root.get_children().filter(slug=slug).specific().first()
            if existing is not None:
                if not isinstance(existing, SectionPage):
                    self.stdout.write(
                        self.style.WARNING(
                            f"跳过 /{slug}/：已存在非板块页「{existing.title}」，不触碰。"
                        )
                    )
                else:
                    self.stdout.write(f"跳过 /{slug}/：板块页「{title}」已存在（幂等）。")
                skipped += 1
                continue
            page = SectionPage(title=title, slug=slug)
            root.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"创建并发布 /{slug}/ 「{title}」。"))
            created += 1

        total = root.get_children().filter(slug__in=[s["slug"] for s in SECTIONS]).count()
        self.stdout.write(f"完成：新建 {created}，跳过 {skipped}，五板块就位 {total}/5。")
