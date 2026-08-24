"""最小冒烟测试（M1 工程基座）。

覆盖计划 03 S1/MB1 的冒烟要求：首页 200、Wagtail admin 登录页 200。
"""

import pytest


@pytest.mark.django_db
def test_home_page_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_wagtail_admin_login_page_returns_200(client):
    response = client.get("/admin/login/")

    assert response.status_code == 200
