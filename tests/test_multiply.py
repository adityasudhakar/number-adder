from fastapi.testclient import TestClient

from number_adder import multiply
from number_adder.server import app


client = TestClient(app)


def test_multiply_logic_positive_numbers():
    assert multiply(3, 4) == 12


def test_multiply_logic_with_zero():
    assert multiply(0, 5) == 0


def test_multiply_logic_negative_numbers():
    assert multiply(-2, 3) == -6


def test_multiply_endpoint_positive_numbers():
    response = client.get("/multiply", params={"a": 3, "b": 4})
    assert response.status_code == 200
    assert response.json() == {"result": 12}


def test_multiply_endpoint_with_zero():
    response = client.get("/multiply", params={"a": 0, "b": 5})
    assert response.status_code == 200
    assert response.json() == {"result": 0}


def test_multiply_endpoint_negative_numbers():
    response = client.get("/multiply", params={"a": -2, "b": 3})
    assert response.status_code == 200
    assert response.json() == {"result": -6}
