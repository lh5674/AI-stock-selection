import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_does_not_expose_secrets(self):
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "example-secret"}):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ai_configured"])
        self.assertNotIn("example-secret", response.text)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_market_response_shape(self):
        with patch("main.get_hot_sectors_a", return_value=[{"板块名称": "半导体", "涨跌幅": 1.2, "最新价": 10}]):
            response = self.client.get("/api/sectors/a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["板块名称"], "半导体")

    def test_invalid_a_share_code_returns_422(self):
        response = self.client.get("/api/stock/a/not-a-code")
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
