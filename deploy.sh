#!/bin/bash

echo "🚀 Starting deployment process for crawl4ai-news-fetcher..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Install build tools
echo "📦 Installing build tools..."
pip install build twine wheel setuptools --upgrade

# Build package
echo "🏗️ Building package..."
python -m build

# Check if build was successful
if [ ! -f "dist/crawl4ai_news_fetcher-0.1.0-py3-none-any.whl" ]; then
    echo "❌ Build failed! No wheel file created."
    echo "📁 Current directory contents:"
    ls -la
    echo "📁 src directory contents:"
    ls -la src/
    exit 1
fi

echo "✅ Build successful!"
echo "📁 Distribution files created:"
ls -la dist/

# Check package
echo "🔍 Checking package..."
python -m twine check dist/*

# Test installation locally
echo "🧪 Testing local installation..."
pip install dist/crawl4ai_news_fetcher-0.1.0-py3-none-any.whl

# Test import
echo "🧪 Testing import..."
python -c "from crawl4ai_news_fetcher import NewsContentFetcher; print('✅ Package imports successfully!')"

echo ""
echo "🎉 Package is ready for deployment!"
echo ""
echo "To upload to Test PyPI (recommended first):"
echo "python -m twine upload --repository testpypi dist/*"
echo ""
echo "To upload to PyPI:"
echo "python -m twine upload dist/*"
echo ""
echo "After uploading, users can install with:"
echo "pip install crawl4ai-news-fetcher"
