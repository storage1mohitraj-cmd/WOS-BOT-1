import asyncio
import types

import pytest

from cogs import gift_operationsapi


def _disable_background_tasks(monkeypatch):
    # Prevent GiftCodeAPI from scheduling its background start task during tests
    monkeypatch.setattr(asyncio, "create_task", lambda coro: None)


def test_handle_api_error_rate_limit(monkeypatch):
    _disable_background_tasks(monkeypatch)
    api = gift_operationsapi.GiftCodeAPI(bot=object())

    class Resp:
        pass

    resp = Resp()
    resp.status = 429

    # Synchronous run of async helper
    backoff = asyncio.run(api._handle_api_error(resp, ""))

    assert isinstance(backoff, float) or isinstance(backoff, int)
    assert backoff >= api.cloudflare_backoff_time


def test_handle_api_error_server_error(monkeypatch):
    _disable_background_tasks(monkeypatch)
    api = gift_operationsapi.GiftCodeAPI(bot=object())

    class Resp:
        pass

    resp = Resp()
    resp.status = 502

    backoff = asyncio.run(api._handle_api_error(resp, "server error"))

    assert isinstance(backoff, float) or isinstance(backoff, int)
    # For server errors we expect some positive backoff
    assert backoff > 0
