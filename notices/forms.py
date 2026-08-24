"""通知/文章 app 表单（CONTENT_MODEL §12 表单闸）。

ControlledTagField：受控标签编辑表单控件——仅从词表选择的多选框，
无自由输入（CM-08 三道闸之表单闸；控件呈现为复选词表，未知值在
字段校验层即被 ModelMultipleChoiceField 拒绝）。
"""

from django import forms

from notices.models import Tag


class ControlledTagField(forms.ModelMultipleChoiceField):
    """受控标签字段：queryset 恒为词表全集，仅选择器语义。"""

    def __init__(self, queryset=None, **kwargs):
        kwargs.setdefault("label", "受控标签")
        kwargs.setdefault("help_text", "仅可从受控标签词表中选择（词表由总管理员维护）")
        kwargs.setdefault("required", False)  # §5.1：受控标签可选（0..n）
        kwargs.setdefault("widget", forms.CheckboxSelectMultiple)
        super().__init__(queryset if queryset is not None else Tag.objects.all(), **kwargs)
