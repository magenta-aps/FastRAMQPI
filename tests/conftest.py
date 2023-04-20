# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
# pylint: disable=redefined-outer-name
"""This module contains pytest specific code, fixtures and helpers."""
from typing import Any
from typing import Callable
from typing import Generator
from unittest.mock import AsyncMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient

from fastramqpi.main import FastRAMQPI


@pytest.fixture()
def set_settings(
    monkeypatch: MonkeyPatch,
) -> Generator[Callable[..., None], None, None]:
    """Set settings via kwargs callback."""

    def _inner(**kwargs: Any) -> None:
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)

    yield _inner


@pytest.fixture(autouse=True)
def setup_client_secret(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Set the CLIENT_SECRET environmental variable to hunter2 by default."""
    monkeypatch.setenv("CLIENT_ID", "orggatekeeper")
    monkeypatch.setenv("CLIENT_SECRET", "hunter2")
    monkeypatch.setenv("AMQP__URL", "amqp://guest:guest@msg_broker:5672/os2mo")
    yield


@pytest.fixture
def teardown_client_secret(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Set the CLIENT_SECRET environmental variable to hunter2 by default."""
    monkeypatch.delenv("CLIENT_SECRET")
    yield


@pytest.fixture(autouse=True)
def disable_metrics(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Disable metrics by setting ENABLE_METRICS to false by default."""
    monkeypatch.setenv("ENABLE_METRICS", "false")
    yield


@pytest.fixture
def enable_metrics(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Enable metrics by setting ENABLE_METRICS to true on demand."""
    monkeypatch.setenv("ENABLE_METRICS", "true")
    yield


@pytest.fixture
def fastramqpi_builder() -> Generator[Callable[[], FastRAMQPI], None, None]:
    """Fixture for generating FastRAMQPI instances."""
    # pylint: disable=unnecessary-lambda
    yield lambda: FastRAMQPI("test")


@pytest.fixture
def fastramqpi(
    fastramqpi_builder: Callable[[], FastRAMQPI]
) -> Generator[FastRAMQPI, None, None]:
    """Fixture for the FastRAMQPI instance."""
    yield fastramqpi_builder()


@pytest.fixture
def test_client_builder(
    fastramqpi_builder: Callable[[], FastRAMQPI]
) -> Generator[Callable[[], TestClient], None, None]:
    """Fixture for generating FastRAMQPI / FastAPI test clients."""

    def create_test_client(fastramqpi: FastRAMQPI | None = None) -> TestClient:
        if fastramqpi is None:
            fastramqpi = fastramqpi_builder()
        return TestClient(fastramqpi.get_app())

    yield create_test_client


@pytest.fixture
def test_client(
    test_client_builder: Callable[[], TestClient]
) -> Generator[TestClient, None, None]:
    """Fixture for the FastAPI test client."""
    yield test_client_builder()


@pytest.fixture
def graphql_session() -> Generator[AsyncMock, None, None]:
    """Fixture for the GraphQL session."""
    yield AsyncMock()


@pytest.fixture
def model_client() -> Generator[AsyncMock, None, None]:
    """Fixture for the ModelClient."""
    yield AsyncMock()
