"""部门 app 表单（CONTENT_MODEL §1.4/§4）。

- ``ParentContextPageForm``：把后台提交流程中的父级注入 page 实例
  （``_provisional_parent``），使 ``clean()`` 在页面入树前即可解析
  所属板块/父容器（§1.4"创建表单的父容器在提交流程中可得"）。
- ``DepartmentContainerForm``：容器 slug 默认取 ``department.slug``
  （§4/IA §4.1——URL 部门段，编辑器未手工填写时生效）。
"""

from wagtail.admin.forms import WagtailAdminPageForm


class ParentContextPageForm(WagtailAdminPageForm):
    """内容页/容器通用基表单：提交流程中向实例注入父级上下文。"""

    def __init__(self, data=None, files=None, parent_page=None, subscription=None, *args, **kwargs):
        super().__init__(
            data, files, *args, parent_page=parent_page, subscription=subscription, **kwargs
        )
        # 仅创建流程注入（编辑流程树内父级可得；parent_page 由 Wagtail 后台
        # CreateView 传入，EditView 不传或传 None）。
        if parent_page is not None and self.instance.pk is None:
            self.instance._provisional_parent = parent_page.specific


class DepartmentContainerForm(ParentContextPageForm):
    """部门容器表单：slug 默认＝department.slug（CONTENT_MODEL §4）。"""

    def __init__(self, data=None, files=None, parent_page=None, subscription=None, *args, **kwargs):
        if data is not None and not data.get("slug"):
            # 部门名称为中文时标题派生 slug 常为空；空则回填所选部门的代号
            # （§4：容器 slug 默认取 department.slug，URL 部门段）。
            # Department 迟导入：departments.models 顶层导入本表单类，反向顶层
            # 导入会成环（forms 仅运行时需要 Department）。
            from departments.models import Department

            department_id = data.get("department")
            if department_id:
                try:
                    slug = Department.objects.values_list("slug", flat=True).get(pk=department_id)
                except (Department.DoesNotExist, ValueError, TypeError):
                    slug = None
                if slug:
                    data = data.copy()
                    data["slug"] = slug
        super().__init__(
            data, files, *args, parent_page=parent_page, subscription=subscription, **kwargs
        )
