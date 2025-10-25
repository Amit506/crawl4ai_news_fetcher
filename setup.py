from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="crawl4ai-news-fetcher",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A specialized news content fetcher with redirect resolution built on crawl4ai",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "setuptools>=45.0",  # Added setuptools
        "crawl4ai>=0.5.0",
        "httpx>=0.24.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "cssselect>=1.2.0",
        "playwright>=1.40.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0",
            "isort>=5.12",
        ],
    },
    keywords="web-scraping, news, content-fetcher, redirect-resolver, crawl4ai",
    url="https://github.com/yourusername/crawl4ai-news-fetcher",
       entry_points={
        'console_scripts': [
            'crawl4ai-install-browsers=crawl4ai_news_fetcher.install:install_browsers',
        ],
    },
)