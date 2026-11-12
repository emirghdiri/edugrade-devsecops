"""Bonus 2 — XSS réfléchi : le terme recherché doit être échappé à l'affichage."""

import pytest

from ..conftest import TEACHER, login

pytestmark = pytest.mark.security

PAYLOAD = "<script>alert(1)</script>"


def test_search_term_is_escaped(client):
    login(client, TEACHER)
    html = client.get("/teacher/students", query_string={"q": PAYLOAD}).get_data(as_text=True)
    assert PAYLOAD not in html, "XSS : le script recherché est renvoyé sans échappement"
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
