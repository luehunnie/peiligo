"""公开内容 API 的 Pydantic 响应模型。

Python 字段名保持 snake_case，JSON 输出使用 camelCase 别名。
不暴露 created_at / updated_at 等内部字段。
"""

from pydantic import BaseModel, ConfigDict, Field

# 板块专属字段允许的值类型：string / number / boolean / string[]
ExtraValue = str | int | float | bool | list[str]


class ContentItemResponse(BaseModel):
    """单条公开内容的响应模型，字段对齐前端冻结契约 ContentItem。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    content_type: str = Field(alias="contentType")
    title: str
    summary: str
    body: list[str]
    source_name: str | None = Field(default=None, alias="sourceName")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    published_at: str = Field(alias="publishedAt")
    status: str
    # 始终输出对象（含空对象 {}），与冻结契约 extraData?: ContentExtraData 对齐，不输出 null
    extra_data: dict[str, ExtraValue] = Field(alias="extraData")
