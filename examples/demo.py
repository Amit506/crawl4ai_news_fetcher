
import asyncio
import json
from crawl4ai_news_fetcher import NewsContentFetcher


async def main():
    url = "https://www.evernote.com/OAuth.action?oauth_token=internal-dev.14CD91FCE1F.687474703A2F2F6C6F63616C686F7374.6E287AD298969B6F8C0B4B1D67BCAB1D"

    async with NewsContentFetcher() as fetcher:
        result = await fetcher.fetch(url)

        if result:
            print("✅ Successfully fetched content!")
            print(f"Final URL: {result['final_url']}")
            print(f"Raw Markdown length: {len(result['markdown_raw'])}")
            print(f"Filtered Markdown length: {len(result['markdown_filtered'])}")
            print(f"HTML length: {len(result['html'])}")
            
            # Save to file
            with open("output.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("📁 Results saved to output.json")
        else:
            print("❌ Failed to fetch content")


if __name__ == "__main__":
    asyncio.run(main())