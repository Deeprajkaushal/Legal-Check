import ipaddress
import json
import re
import socket
from typing import Dict, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 "
    "LegalCheck/1.0"
)

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB
TIMEOUT_SECONDS = 10


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Validates URL scheme and guards against SSRF / private network requests.
    Returns (is_safe, error_message).
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."

    url_trimmed = url.strip()

    parsed = urlparse(url_trimmed)
    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Only http:// and https:// URLs are supported."

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid URL hostname."

    # Check for obvious internal/localhost hostnames
    if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return False, "Access to private or local network addresses is restricted."

    try:
        # Resolve hostname to IP address to prevent DNS rebinding SSRF
        ip_str = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip_str)

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
            return False, f"Access to private or local IP ranges ({ip_str}) is restricted."
    except socket.gaierror:
        return False, f"Could not resolve domain name '{hostname}'."
    except Exception as err:
        return False, f"URL validation error: {str(err)}"

    return True, ""


def extract_json_ld(soup: BeautifulSoup) -> list:
    """Extracts Product/Offer structured JSON-LD objects from BeautifulSoup parsed tree."""
    json_ld_blocks = []
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string.strip())
            if isinstance(data, list):
                json_ld_blocks.extend(data)
            elif isinstance(data, dict):
                json_ld_blocks.append(data)
        except (json.JSONDecodeError, Exception):
            continue

    # Filter JSON-LD for product relevant schemas
    relevant = []
    for item in json_ld_blocks:
        if isinstance(item, dict):
            graph = item.get("@graph")
            if isinstance(graph, list):
                for node in graph:
                    if isinstance(node, dict) and _is_product_schema(node):
                        relevant.append(node)
            elif _is_product_schema(item):
                relevant.append(item)

    return relevant if relevant else json_ld_blocks[:3]


def _is_product_schema(obj: dict) -> bool:
    schema_type = obj.get("@type", "")
    if isinstance(schema_type, list):
        types_lower = [str(t).lower() for t in schema_type]
        return any("product" in t or "offer" in t for t in types_lower)
    type_str = str(schema_type).lower()
    return "product" in type_str or "offer" in type_str or "itempage" in type_str


def fetch_and_extract_web_content(url: str) -> Dict[str, Any]:
    """
    Fetches public web page content and extracts structured metadata and visible text.
    """
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        return {
            "success": False,
            "reason": "security_error",
            "message": error_msg,
            "url": url,
        }

    parsed = urlparse(url.strip())
    domain = parsed.hostname or ""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(
            url.strip(),
            headers=headers,
            timeout=TIMEOUT_SECONDS,
            stream=True,
            allow_redirects=True,
        )

        # Verify intermediate redirect URLs for safety
        for hist_resp in response.history:
            hist_safe, hist_err = is_safe_url(hist_resp.url)
            if not hist_safe:
                return {
                    "success": False,
                    "reason": "security_error",
                    "message": f"Redirect blocked: {hist_err}",
                    "url": url,
                    "domain": domain,
                }
        final_safe, final_err = is_safe_url(response.url)
        if not final_safe:
            return {
                "success": False,
                "reason": "security_error",
                "message": f"Redirect blocked: {final_err}",
                "url": url,
                "domain": domain,
            }

        if response.status_code != 200:
            return {
                "success": False,
                "reason": "http_error",
                "message": f"Webpage returned HTTP status code {response.status_code}.",
                "url": url,
                "domain": domain,
            }

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type and "text/plain" not in content_type:
            return {
                "success": False,
                "reason": "invalid_content_type",
                "message": f"URL did not return HTML content (Content-Type: {content_type}).",
                "url": url,
                "domain": domain,
            }

        # Download response up to MAX_RESPONSE_SIZE
        raw_bytes = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            raw_bytes.extend(chunk)
            if len(raw_bytes) > MAX_RESPONSE_SIZE:
                break

        html_text = raw_bytes.decode(response.encoding or "utf-8", errors="replace")

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "reason": "timeout",
            "message": f"Request to webpage timed out after {TIMEOUT_SECONDS} seconds.",
            "url": url,
            "domain": domain,
        }
    except requests.exceptions.RequestException as err:
        return {
            "success": False,
            "reason": "network_error",
            "message": f"Failed to connect to product webpage: {str(err)}",
            "url": url,
            "domain": domain,
        }

    soup = BeautifulSoup(html_text, "html.parser")

    # Extract Page Title
    page_title = ""
    if soup.title and soup.title.string:
        page_title = soup.title.string.strip()
    if not page_title:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            page_title = str(og_title.get("content")).strip()

    # Extract Canonical URL
    canonical_url = url.strip()
    canonical_tag = soup.find("link", rel=re.compile(r"canonical", re.I))
    if canonical_tag and canonical_tag.get("href"):
        canonical_url = str(canonical_tag.get("href")).strip()

    # Extract JSON-LD structured data
    json_ld_data = extract_json_ld(soup)

    # Extract Meta Descriptions & OpenGraph declarations
    meta_details = []
    for meta_name in ("description", "og:description", "og:title", "keywords"):
        tag = soup.find("meta", attrs={"name": meta_name}) or soup.find("meta", attrs={"property": meta_name})
        if tag and tag.get("content"):
            meta_details.append(f"{meta_name}: {tag.get('content')}")

    # Strip noise elements
    for noise_tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe", "svg"]):
        noise_tag.decompose()

    # Extract main content visible text
    visible_text = soup.get_text(separator="\n", strip=True)

    # Clean whitespace and multiple blank lines
    cleaned_lines = [line.strip() for line in visible_text.splitlines() if line.strip()]
    cleaned_text = "\n".join(cleaned_lines)

    # Check if text length or JSON-LD is sufficient
    total_content_length = len(cleaned_text)
    if total_content_length < 100 and not json_ld_data:
        return {
            "success": False,
            "reason": "insufficient_content",
            "message": "Digital inspection could not extract sufficient product information from this page.",
            "url": url,
            "domain": domain,
            "page_title": page_title,
        }

    # Truncate text to ~10,000 characters for LLM prompt safety
    truncated_text = cleaned_text[:10000]

    from datetime import datetime, timezone

    return {
        "success": True,
        "url": url,
        "canonical_url": canonical_url,
        "domain": domain,
        "page_title": page_title or domain,
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "meta_details": meta_details,
        "json_ld": json_ld_data,
        "extracted_text": truncated_text,
    }
