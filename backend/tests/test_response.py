# -*- coding: utf-8 -*-
from app.core.response import error_response, success_response


def test_success_response_default_data():
    response = success_response()

    assert response.success is True
    assert response.code == "OK"
    assert response.message == "success"
    assert response.data == {}
    assert response.request_id is None


def test_error_response_default_data():
    response = error_response(code="TEST_ERROR", message="test failed")

    assert response.success is False
    assert response.code == "TEST_ERROR"
    assert response.message == "test failed"
    assert response.data is None
    assert response.request_id is None