# Crawl4AI News Fetcher

A specialized Python package for fetching news content with intelligent redirect resolution, built on top of [crawl4ai](https://github.com/unclecode/crawl4ai).

## Features

- **Smart Redirect Resolution**: Automatically resolves redirects from services like Google News, bit.ly, etc.
- **Multi-method Resolution**: Uses HTTP, HTML parsing, and browser automation for robust redirect resolution
- **Content Extraction**: Extracts clean markdown and HTML content from news articles
- **Query-focused Filtering**: Uses BM25 algorithm to filter content based on user queries
- **Async Support**: Fully asynchronous for high-performance scraping

## Installation

```bash
pip install crawl4ai-news-fetcher