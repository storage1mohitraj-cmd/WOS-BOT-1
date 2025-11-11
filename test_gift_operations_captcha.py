import asyncio
import base64

import pytest

from cogs import gift_operations_captcha as captcha_mod


class DummyLogger:
    def info(self, *a, **k):
        pass
    def warning(self, *a, **k):
        pass
    def error(self, *a, **k):
        pass
    def exception(self, *a, **k):
        pass


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


class DummySession:
    def __init__(self, captcha_b64=None, redeem_json=None):
        self.captcha_b64 = captcha_b64
        self.redeem_json = redeem_json or {"msg": "SUCCESS", "err_code": 0}

    def mount(self, *a, **k):
        pass

    def post(self, url, headers=None, data=None):
        if 'captcha' in url:
            return DummyResponse(200, {"data": {"img": self.captcha_b64}})
        else:
            return DummyResponse(200, self.redeem_json)


def make_dummy_gift_ops():
    class G:
        pass

    g = G()
    g.retry_config = None
    g.wos_giftcode_redemption_url = "https://example.com"
    g.wos_captcha_url = "https://example.com/captcha"
    g.wos_giftcode_url = "https://example.com/redeem"
    g.encode_data = lambda d: d
    g.logger = DummyLogger()
    g.giftlog = DummyLogger()
    g.processing_stats = {"ocr_solver_calls": 0, "ocr_valid_format": 0, "captcha_submissions": 0, "server_validation_success": 0, "server_validation_failure": 0}

    class Solver:
        async def solve_captcha(self, image_bytes, fid=None, attempt=0):
            return ("ABCD", True, "ONNX", 0.9, None)
    g.captcha_solver = Solver()

    return g


def test_fetch_captcha_success():
    g = make_dummy_gift_ops()
    # simple 1x1 PNG base64
    png_b64 = 'data:image/png;base64,' + base64.b64encode(b'PNG').decode()
    session = DummySession(captcha_b64=png_b64)

    img_b64, err = asyncio.run(captcha_mod.fetch_captcha(g, '123', session=session))
    assert err is None
    assert img_b64 is not None


def test_attempt_gift_code_success():
    g = make_dummy_gift_ops()
    png_b64 = 'data:image/png;base64,' + base64.b64encode(b'PNG').decode()
    session = DummySession(captcha_b64=png_b64, redeem_json={"msg": "SUCCESS", "err_code": 0})

    status, image_bytes, captcha_code, method = asyncio.run(captcha_mod.attempt_gift_code_with_api(g, '244886619', 'TESTCODE', session))
    assert status == 'SUCCESS'
    assert captcha_code == 'ABCD'
