"""
Crawl4AI News Fetcher - A specialized news content fetcher with redirect resolution.
"""

from .redirect_resolver import RedirectResolver
from .content_fetcher import NewsContentFetcher

__version__ = "0.1.0"
__all__ = ["RedirectResolver", "NewsContentFetcher"]