"""M3.4 search_fields 反射与契约常量测试（CONTENT_MODEL §20.1/§21.1/§23）。

断言面：§20.1 表 A/B 逐页 search_fields 与冻结映射零漂移（含 boost 档位
高=2/中=缺省/低=0.5 与 RelatedFields 嵌套）；PS-30/PS-32 声明面守护；
PS-36 type 五值单射；§23 金标集契约占位常量。纯类级反射，零数据库。
"""

from django.test import SimpleTestCase
from guides.models import GuidePage
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from search import services
from wagtail.search import index


def _spec(fields):
    """search_fields → {字段名: [(字段类, boost)]}；RelatedFields → 嵌套 dict。"""
    spec = {}
    for field in fields:
        if isinstance(field, index.RelatedFields):
            spec[field.field_name] = [("RelatedFields", _spec(field.fields))]
        else:
            spec.setdefault(field.field_name, []).append(
                (type(field).__name__, getattr(field, "boost", None))
            )
    return spec


def _base():
    """表 A 五页共同骨架（事实 2 整体遮蔽 → 逐项再声明，缺一即丢）。"""
    return {
        "title": [("SearchField", 2), ("AutocompleteField", None)],
        "live": [("FilterField", None)],
        "expired": [("FilterField", None)],
        "path": [("FilterField", None)],
        "first_published_at": [("FilterField", None)],
        "department": [
            ("RelatedFields", {"name": [("SearchField", None)], "slug": [("FilterField", None)]})
        ],
    }


_TAGS = (
    "RelatedFields",
    {"name": [("SearchField", None), ("FilterField", None)], "slug": [("FilterField", None)]},
)
_VOCAB = ("RelatedFields", {"name": [("SearchField", None), ("FilterField", None)]})
_NA = {
    **_base(),
    "summary": [("SearchField", None)],
    "body": [("SearchField", None)],
    "event_location": [("SearchField", 0.5)],
    "tags": [_TAGS],
}
EXPECTED_SEARCH_FIELDS = {
    NoticePage: _NA,
    ArticlePage: dict(_NA),
    MaterialPage: {
        **_base(),
        "summary": [("SearchField", None)],
        "body": [("SearchField", None)],
        "tags": [_TAGS],
        "discipline": [_VOCAB],
        "material_type": [_VOCAB],
    },
    SoftwareToolPage: {
        **_base(),
        "body": [("SearchField", None)],
        "license_note": [("SearchField", 0.5)],
        "platforms": [_VOCAB],
    },
    GuidePage: {
        **_base(),
        "location": [("SearchField", None)],
        "opening_hours": [("SearchField", None)],
        "contact": [("SearchField", 0.5)],
        "extra_notes": [("SearchField", 0.5)],
        "category": [_VOCAB],
    },
}


class SearchFieldsReflectionTests(SimpleTestCase):
    """PS-30/PS-32：逐页 search_fields 与表 A/B 逐项一致（含 boost 档位）。"""

    def test_search_fields_match_frozen_tables(self):
        for model, expected in EXPECTED_SEARCH_FIELDS.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(_spec(model.search_fields), expected)


class ContractConstantsTests(SimpleTestCase):
    """PS-36 五值单射＋§23 契约占位常量（零漂移守护）。"""

    def test_type_identifier_bijection(self):
        self.assertEqual(
            set(services.TYPE_IDENTIFIERS), {"notice", "article", "material", "software", "guide"}
        )
        models = list(services.TYPE_IDENTIFIERS.values())
        self.assertEqual(len(models), len(set(models)))
        for value, model in services.TYPE_IDENTIFIERS.items():
            self.assertEqual(services.model_for_type(value), model)
            self.assertEqual(services.type_identifier(model), value)
        self.assertIsNone(services.model_for_type("bogus"))

    def test_constants_frozen(self):
        self.assertEqual(
            services.SECTION_SLUGS, ("chronicle", "events", "materials", "software", "guide")
        )
        self.assertEqual(set(services.TYPE_LABELS), set(services.TYPE_IDENTIFIERS))
        self.assertEqual(
            services.GOLDEN_SET_ENTRY_FIELDS,
            ("query", "expected_pages", "required_filters", "notes"),
        )
        self.assertEqual(
            services.POC_FIELD_CONTRACT, ("title", "body", "department", "tags", "category")
        )
