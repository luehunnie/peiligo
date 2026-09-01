"""pytest 全局夹具（F-05 引入）。

django-axes 的 AxesBackend 要求 ``authenticate()`` 必携 request，而
Django test ``Client.login()`` 走无 request 形态（django/test/client.py
L838）——axes 官方口径即测试期全局关停（``@toggleable`` 使后端与处理器
整体旁路，含 request 形参检查）。会话级关停以覆盖 ``setUpTestData`` 内
的 ``build_permission_world`` 登录链（类装置先于函数级夹具执行）；
``tests/test_login_governance.py`` 的 ``AxesLockoutTests`` 以
``override_settings(AXES_ENABLED=True)`` 类级重开（enable 晚于本夹具，
栈内后启用者生效），完整 axes 链路行为级验证不受影响。生产行为以
``peiligo/settings/base.py`` 的 F-05 配置为准，零改动。
"""

import pytest
from django.test import override_settings


@pytest.fixture(autouse=True, scope="session")
def _axes_off_for_pytest():
    with override_settings(AXES_ENABLED=False):
        yield
