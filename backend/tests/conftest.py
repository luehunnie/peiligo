"""Integration test infrastructure for peiligo_test.

Safety guard: parse TEST_DATABASE_URL and hard-assert host/port/database/user
match the frozen test database before any connection is made; any mismatch
aborts the integration tests. We never fall back to DATABASE_URL and never
print the URL or password.

Isolation: each integration test receives its own connection bound to a single
transaction that is rolled back on teardown, so no business data is ever
committed and tests do not depend on one another.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine

from app.config import TEST_DATABASE_URL

# Frozen connection expectations for the test database.
_HOST = "127.0.0.1"
_PORT = 5432
_DATABASE = "peiligo_test"
_USER = "peiligo_test_user"


def _assert_test_db_guard(url: str) -> None:
    """Abort immediately unless the URL points exactly at peiligo_test."""
    parsed = urlparse(url)
    # Compare component-wise only; the password is never inspected or printed.
    assert parsed.scheme.startswith("postgresql"), "TEST_DATABASE_URL scheme mismatch"
    assert parsed.hostname == _HOST, "TEST_DATABASE_URL host mismatch (aborting)"
    assert parsed.port == _PORT, "TEST_DATABASE_URL port mismatch (aborting)"
    assert (parsed.path or "").lstrip("/") == _DATABASE, (
        "TEST_DATABASE_URL database mismatch (aborting)"
    )
    assert parsed.username == _USER, "TEST_DATABASE_URL user mismatch (aborting)"


@pytest.fixture(scope="session")
def pg_engine():
    _assert_test_db_guard(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def pg_conn(pg_engine):
    connection = pg_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        # Roll back unconditionally: covers both pending and aborted (e.g.
        # IntegrityError) transactions, leaving zero committed rows.
        transaction.rollback()
        connection.close()
