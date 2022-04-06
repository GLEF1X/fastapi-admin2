from typing import Any, Dict

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from fastapi_admin2.i18n import Translator, I18nMiddleware
from fastapi_admin2.i18n import get_i18n, lazy_gettext, gettext
from tests.conftest import DATA_DIR


@pytest.fixture(name="i18n")
def i18n_fixture() -> Translator:
    return Translator(path_to_default_translations=DATA_DIR / "locales")


@pytest.fixture(name="i18n_extra")
def i18n_fixture_with_extra_translations():
    return Translator(path_to_default_translations=DATA_DIR / "locales",
                      path_to_extra_translations=DATA_DIR / "extra_locales")


class TestI18nCore:
    def test_init(self, i18n: Translator):
        assert set(i18n.available_locales) == {"en", "uk"}

    def test_reload(self, i18n: Translator):
        i18n.reload_locales()
        assert set(i18n.available_locales) == {"en", "uk"}

    def test_current_locale(self, i18n: Translator):
        assert i18n.current_locale == "en"
        i18n.current_locale = "uk"
        assert i18n.current_locale == "uk"
        assert i18n.ctx_locale.get() == "uk"

    def test_use_locale(self, i18n: Translator):
        assert i18n.current_locale == "en"
        with i18n.use_locale("uk"):
            assert i18n.current_locale == "uk"
            with i18n.use_locale("it"):
                assert i18n.current_locale == "it"
            assert i18n.current_locale == "uk"
        assert i18n.current_locale == "en"

    def test_get_i18n(self, i18n: Translator):
        with pytest.raises(LookupError):
            get_i18n()

        with i18n.internationalized():
            assert get_i18n() == i18n

    @pytest.mark.parametrize(
        "locale,case,result",
        [
            [None, dict(singular="test"), "test"],
            [None, dict(singular="test", locale="uk"), "тест"],
            ["en", dict(singular="test", locale="uk"), "тест"],
            ["uk", dict(singular="test", locale="uk"), "тест"],
            ["uk", dict(singular="test"), "тест"],
            ["it", dict(singular="test"), "test"],
            [None, dict(singular="test", n=2), "test"],
            [None, dict(singular="test", n=2, locale="uk"), "тест"],
            ["en", dict(singular="test", n=2, locale="uk"), "тест"],
            ["uk", dict(singular="test", n=2, locale="uk"), "тест"],
            ["uk", dict(singular="test", n=2), "тест"],
            ["it", dict(singular="test", n=2), "test"],
            [None, dict(singular="test", plural="test2", n=2), "test2"],
            [None, dict(singular="test", plural="test2", n=2, locale="uk"), "test2"],
            ["en", dict(singular="test", plural="test2", n=2, locale="uk"), "test2"],
            ["uk", dict(singular="test", plural="test2", n=2, locale="uk"), "test2"],
            ["uk", dict(singular="test", plural="test2", n=2), "test2"],
            ["it", dict(singular="test", plural="test2", n=2), "test2"],
        ],
    )
    def test_gettext(self, i18n: Translator, locale: str, case: Dict[str, Any], result: str):
        if locale is not None:
            i18n.current_locale = locale
        with i18n.internationalized():
            assert i18n.gettext(**case) == result
            assert str(i18n.lazy_gettext(**case)) == result
            assert gettext(**case) == result
            assert str(lazy_gettext(**case)) == result


async def next_call(r: Request):
    return gettext("test")


@pytest.mark.asyncio
class TestSimpleI18nMiddleware:
    @pytest.mark.parametrize(
        "req,expected_result",
        [
            [Request(scope={
                "type": "http",
                "query_string": b"language=uk"
            }), "тест"],
            [Request(scope={
                "type": "http",
                "query_string": b'language=en'
            }), "test"],
        ],
    )
    async def test_middleware(self, i18n: Translator, req: Request, expected_result: str):
        middleware = I18nMiddleware(app=FastAPI(), translator=i18n)
        result = await middleware.dispatch(
            req,
            next_call
        )
        assert result == expected_result
