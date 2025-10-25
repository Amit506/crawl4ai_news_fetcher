import asyncio
import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx
from playwright.async_api import async_playwright

# try:
#     from playwright.async_api import async_playwright
PLAYWRIGHT_AVAILABLE = True
# except ImportError:
#     PLAYWRIGHT_AVAILABLE = False


class RedirectResolver:
    def __init__(self, timeout: int = 15, user_agent: str = None, verbose: bool = True):
        self.timeout = timeout
        self.verbose = verbose
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/132.0.0.0 Safari/537.36"
        )

        self.gnews_batch_url = (
            "https://news.google.com/_/DotsSplashUi/data/batchexecute"
        )
        self.gnews_headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "user-agent": self.user_agent,
            "referer": "https://news.google.com/",
            "origin": "https://news.google.com",
        }

    async def _resolve_internal(self, url: str) -> str:
        """
        Core internal resolver that tries multiple methods in sequence
        to find the true final redirect target.
        """

        if "news.google.com/rss/articles/" in url:
            resolved = await self._resolve_google_news(url)
            if resolved:
                if self.verbose:
                    print(f"✅ [GoogleNews] Resolved via _resolve_internal: {resolved}")
                return resolved

        resolved = await self._resolve_http(url)
        if resolved and not self._is_redirect_domain(resolved):
            if self.verbose:
                print(f"✅ [HTTP] Resolved via _resolve_internal: {resolved}")
            return resolved

        resolved = await self._resolve_html(url)
        if resolved and not self._is_redirect_domain(resolved):
            if self.verbose:
                print(f"✅ [HTML] Resolved via _resolve_internal: {resolved}")
            return resolved

        # 4️⃣ Try Chromium (Playwright) fallback
        if PLAYWRIGHT_AVAILABLE:
            resolved = await self._resolve_chromium(url)
            if resolved and not self._is_redirect_domain(resolved):
                if self.verbose:
                    print(f"✅ [Chromium] Resolved via _resolve_internal: {resolved}")
                return resolved
        else:
            if self.verbose:
                print("⚠️ Playwright not available, skipping Chromium resolution")

        # 5️⃣ None succeeded — return original
        if self.verbose:
            print("⚠️ All resolution methods failed, returning original URL")
        return url

    async def resolve(self, url: str) -> str:
        """Unified redirect resolver with pre-check to avoid unnecessary processing."""
        if self.verbose:
            print(f"\n🔍 Resolving: {url}")

        # Ensure URL is a string
        url = str(url)

        # ✅ FIRST: Check if redirect resolution is even needed
        if not self._needs_redirect_resolution(url):
            if self.verbose:
                print("✅ No redirect resolution needed - returning original URL")
            return url

        try:
            # Set overall timeout for the entire resolution process
            return await asyncio.wait_for(
                self._resolve_internal(url), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            if self.verbose:
                print(
                    f"⏰ Overall timeout after {self.timeout}s, returning original URL"
                )
            return url
        except Exception as e:
            if self.verbose:
                print(f"❌ Resolution failed: {e}, returning original URL")
            return url

    def _needs_redirect_resolution(self, url: str) -> bool:
        """Check if this URL actually needs redirect resolution."""

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if it's a known redirect service (redirect IS needed)
            redirect_domains = [
                "news.google.com",
                "bit.ly",
                "goo.gl",
                "t.co",
                "tinyurl.com",
                "ow.ly",
                "buff.ly",
                "ift.tt",
                "dlvr.it",
            ]

            for redirect_domain in redirect_domains:
                if domain == redirect_domain or domain.endswith("." + redirect_domain):
                    if self.verbose:
                        print(f"🔍 Redirect domain detected: {domain}")
                    return True

            # Check URL patterns that indicate redirects
            redirect_patterns = [
                r"/rss/articles/",  # Google News RSS
                r"/amp/",  # AMP pages might need canonical resolution
                r"/url\?q=",  # Google redirect URLs
                r"utm_",  # Tracking parameters
            ]

            for pattern in redirect_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    if self.verbose:
                        print(f"🔍 Redirect pattern detected: {pattern}")
                    return True

            # Default: Assume direct URL (no redirect needed)
            if self.verbose:
                print("✅ Assuming direct URL - no redirect resolution needed")
            return True

        except Exception as e:
            if self.verbose:
                print(f"⚠️ Error checking redirect need: {e}")
            # On error, assume it needs resolution to be safe
            return True

    async def _resolve_google_news(self, url: str) -> str | None:
        """Resolve a Google News RSS 'articles/...' URL to the publisher URL."""
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": self.user_agent,
                    "Referer": "https://news.google.com/",
                },
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:

                # 1️⃣ Try a fast simple redirect first
                direct = await self._try_simple_redirect(client, url)
                if direct and "news.google.com" not in urlparse(direct).netloc.lower():
                    return direct

                # 2️⃣ Fetch the Google News HTML
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "lxml")

                node = soup.select_one("c-wiz[data-p]")
                if not node:
                    # fallback to html.parser if lxml fails
                    soup = BeautifulSoup(html, "html.parser")
                    node = soup.select_one("c-wiz[data-p]")
                if not node:
                    # fallback again: meta-refresh or first non-Google link
                    return await self._extract_fallback_url(client, html, url)

                data_p = node.get("data-p")
                if not data_p:
                    return await self._extract_fallback_url(client, html, url)

                # 3️⃣ Parse data-p JSON (robust conversion)
                obj = json.loads(data_p.replace("%.@.", '["garturlreq",'))
                payload_obj = obj[:-6] + obj[-2:]
                payload = {
                    "f.req": json.dumps(
                        [[["Fbv4je", json.dumps(payload_obj), "null", "generic"]]]
                    )
                }

                # 4️⃣ Call Google's hidden batchexecute API
                r = await client.post(
                    self.gnews_batch_url, headers=self.gnews_headers, data=payload
                )
                r.raise_for_status()
                txt = r.text.replace(")]}'", "", 1).strip()
                outer = json.loads(txt)

                article_url = None
                for item in outer:
                    if isinstance(item, list) and len(item) >= 3 and item[2]:
                        try:
                            inner = json.loads(item[2])
                            if (
                                isinstance(inner, list)
                                and len(inner) >= 2
                                and isinstance(inner[1], str)
                            ):
                                article_url = inner[1]
                                break
                        except Exception:
                            continue

                if article_url:
                    return article_url

                # fallback again if nothing found
                return await self._extract_fallback_url(client, html, url)

        except Exception as e:
            if self.verbose:
                print(f"⚠️ GoogleNews resolve failed: {e}")
            return None

    async def _extract_fallback_url(
        self, client: httpx.AsyncClient, html: str, base_url: str
    ) -> str | None:
        """Fallback method if Google News batchexecute fails."""
        soup = BeautifulSoup(html, "html.parser")

        # Meta refresh
        meta = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
        if meta and meta.get("content"):
            m = re.search(r"url=([^;]+)", meta["content"], re.I)
            if m:
                found = m.group(1).strip("'\" ")
                return urljoin(base_url, found)

        # First non-Google anchor
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and not self._is_redirect_domain(href):
                return href

        # Final attempt: follow redirect chain
        return await self._try_simple_redirect(client, base_url)

    async def _try_simple_redirect(
        self, client: httpx.AsyncClient, url: str
    ) -> str | None:
        try:
            resp = await client.get(url, follow_redirects=True)
            final_url = str(resp.url)
            if "news.google.com" not in urlparse(final_url).netloc.lower():
                return final_url
            return None
        except Exception:
            return None

    async def _resolve_http(self, url: str) -> str | None:
        """Resolve redirects using HTTP requests."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            ) as client:
                resp = await client.get(url)
                return str(resp.url)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ HTTP resolve failed: {e}")
            return None

    async def _resolve_html(self, url: str) -> str | None:
        """Resolve redirects by parsing HTML content."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            ) as client:
                resp = await client.get(url)
                final = str(resp.url)
                soup = BeautifulSoup(resp.text, "html.parser")

                # canonical / og / meta-refresh
                for tag in [
                    ("link", {"rel": "canonical"}, "href"),
                    ("meta", {"property": "og:url"}, "content"),
                    ("meta", {"name": "og:url"}, "content"),
                ]:
                    t = soup.find(tag[0], tag[1])
                    if t and t.get(tag[2]):
                        found_url = t[tag[2]]
                        return str(urljoin(final, found_url))

                meta_refresh = soup.find("meta", {"http-equiv": "refresh"})
                if meta_refresh and meta_refresh.get("content"):
                    m = re.search(r"url=(.*)", meta_refresh["content"], flags=re.I)
                    if m:
                        found_url = m.group(1).strip("\"' ")
                        return str(urljoin(final, found_url))

                # JS redirect
                js_match = re.search(
                    r'window\.location(?:\.replace)?\(["\'](.*?)["\']\)', resp.text
                )
                if js_match:
                    found_url = js_match.group(1)
                    return str(urljoin(final, found_url))

                # JSON-LD or first outbound link
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "{}")
                        if isinstance(data, dict) and data.get("url"):
                            found_url = data["url"]
                            return str(urljoin(final, found_url))
                    except Exception:
                        pass

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http") and not self._is_redirect_domain(href):
                        return str(href)

                return None
        except Exception as e:
            if self.verbose:
                print(f"⚠️ HTML resolve failed: {e}")
            return None

    async def _resolve_chromium(self, url: str) -> str | None:
        """Use Playwright as last resort."""
        if not PLAYWRIGHT_AVAILABLE:
            return None
            
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=self.user_agent)
                page = await context.new_page()

                await page.goto(
                    url, timeout=self.timeout * 1000, wait_until="domcontentloaded"
                )

                # Wait for potential redirects
                for _ in range(5):
                    old_url = page.url
                    await page.wait_for_timeout(500)
                    if page.url != old_url:
                        break

                final_url = str(page.url)
                await browser.close()

                # Return None if it's still a redirect domain
                return None if self._is_redirect_domain(final_url) else final_url
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Chromium resolve failed: {e}")
            return None

    def _is_redirect_domain(self, url: str) -> bool:
        """Check if URL is from a known redirect service."""
        if not url:
            return True

        url = str(url)
        domains = [
            "news.google.com",
            "bit.ly",
            "goo.gl",
            "t.co",
            "tinyurl.com",
            "ow.ly",
        ]

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return any(redirect_domain in domain for redirect_domain in domains)
        except Exception:
            return False