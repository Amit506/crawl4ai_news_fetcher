import asyncio
import json
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.async_configs import BrowserConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import BM25ContentFilter

from .redirect_resolver import RedirectResolver


class NewsContentFetcher:
    def __init__(self, concurrency: int = 5, timeout: int = 30):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.browser_cfg = BrowserConfig(
            headless=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            browser_type="chromium",
        )
        self.crawler: AsyncWebCrawler | None = None
        self.resolver = RedirectResolver(timeout=timeout)

    async def __aenter__(self):
        self.crawler = AsyncWebCrawler(config=self.browser_cfg)
        await self.crawler.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc, tb)

    async def fetch(self, url: str, user_query: str | None = None) -> dict | None:
        async with self.semaphore:
            try:
                final_url = await self.resolver.resolve(url)
            except Exception as e:
                print(f"[Resolver] Error resolving {url}: {e}")
                final_url = url

            print(f"🌐 Fetching content from: {final_url} | query={user_query}")

            crawl_config = CrawlerRunConfig(
                deep_crawl_strategy=BFSDeepCrawlStrategy(
                    max_depth=0, include_external=False
                ),
                scraping_strategy=LXMLWebScrapingStrategy(),
                wait_until="domcontentloaded",
                exclude_external_links=True,
                excluded_selector=(
                    "nav, footer, header, aside, "
                    ".navbar, .footer, .header, .sidebar, "
                    ".ads, #navbar, #footer, "
                    "[role='navigation'], [role='banner'], [role='contentinfo']"
                ),
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=BM25ContentFilter(
                        user_query=user_query,
                        bm25_threshold=0.7,
                    )
                ),
            )

            try:
                results = await self.crawler.arun(final_url, config=crawl_config)
                for result in results:
                    if result.markdown:
                        return {
                            "markdown_raw": result.markdown.raw_markdown or "",
                            "markdown_filtered": result.markdown.fit_markdown or "",
                            "html": result.html or "",
                            "final_url": str(final_url),
                        }
                print(f"⚠️ No content extracted for {final_url}")
            except Exception as e:
                print(f"❌ Error fetching {user_query},{final_url}: {e}")

            return None