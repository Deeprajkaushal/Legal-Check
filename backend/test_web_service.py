import unittest
from web.web_service import is_safe_url, fetch_and_extract_web_content

class TestWebService(unittest.TestCase):
    def test_is_safe_url_valid(self):
        is_safe, err = is_safe_url("https://example.com/product/123")
        self.assertTrue(is_safe)
        self.assertEqual(err, "")

    def test_is_safe_url_invalid_scheme(self):
        is_safe, err = is_safe_url("file:///etc/passwd")
        self.assertFalse(is_safe)
        self.assertIn("http:// and https://", err)

    def test_is_safe_url_localhost(self):
        is_safe, err = is_safe_url("http://localhost:8000/secret")
        self.assertFalse(is_safe)
        self.assertIn("restricted", err.lower())

    def test_is_safe_url_private_ip(self):
        is_safe, err = is_safe_url("http://127.0.0.1/admin")
        self.assertFalse(is_safe)
        self.assertIn("restricted", err.lower())

    def test_fetch_public_url(self):
        res = fetch_and_extract_web_content("https://example.com")
        self.assertTrue(res["success"])
        self.assertEqual(res["domain"], "example.com")
        self.assertIn("Example Domain", res["page_title"])

if __name__ == "__main__":
    unittest.main()
