import os
import tempfile
import unittest

from app import create_app


class URLShortenerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": os.path.join(self.temp_dir.name, "test.sqlite3"),
                "PUBLIC_BASE_URL": "https://short.example",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_redirect(self):
        response = self.client.post(
            "/api/shorten",
            json={"url": "https://example.com/a?b=c"},
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["short_url"], f"https://short.example/s/{data['code']}")

        redirect_response = self.client.get(f"/s/{data['code']}")
        self.assertEqual(redirect_response.status_code, 302)
        self.assertEqual(redirect_response.headers["Location"], "https://example.com/a?b=c")

    def test_rejects_non_http_urls(self):
        for url in (
            "javascript:alert(1)",
            "ftp://example.com/file",
            "https://user:password@example.com/",
            "https://example.com:invalid/",
            "https://example.com/with space",
        ):
            with self.subTest(url=url):
                response = self.client.post("/api/shorten", json={"url": url})
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())

    def test_requires_json_and_url(self):
        self.assertEqual(self.client.post("/api/shorten").status_code, 415)
        self.assertEqual(
            self.client.post("/api/shorten", json={"url": ""}).status_code, 400
        )

    def test_unknown_code_returns_json_404(self):
        response = self.client.get("/s/not-found")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Short URL not found."})

    def test_retrieves_link_metadata(self):
        created = self.client.post(
            "/api/shorten", json={"url": "https://example.org"}
        ).get_json()
        response = self.client.get(f"/api/links/{created['code']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["original_url"], "https://example.org")


if __name__ == "__main__":
    unittest.main()
