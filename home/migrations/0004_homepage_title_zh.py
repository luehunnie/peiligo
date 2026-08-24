from django.db import migrations


def retitle_seed_homepage(apps, schema_editor):
    """M2.2（前台 IA）：官方脚手架种子 HomePage 标题 ``Home`` → ``首页``。

    前台为中文站点（IA §2 全部板块名冻结中文，PRD §6），种子标题随
    基础模板首屏（h1/title）输出，保留英文脚手架字样将直接暴露给用户。
    仅重命名仍为脚手架原文的种子（slug=home、depth=2、title="Home"），
    不触碰任何已被运营改过的标题；无匹配即空操作，天然幂等。
    """
    Page = apps.get_model("wagtailcore", "Page")
    Page.objects.filter(slug="home", depth=2, title="Home").update(
        title="首页", draft_title="首页"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0003_sectionpage"),
    ]

    operations = [
        migrations.RunPython(retitle_seed_homepage, migrations.RunPython.noop),
    ]
