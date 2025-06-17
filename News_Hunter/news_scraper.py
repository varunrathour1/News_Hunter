import asyncio
import os
from typing import Dict, List

from aiolimiter import AsyncLimiter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import logging # Add this line at the top

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Add this





from utils import (
    generate_news_urls_to_scrape,
    scrape_with_brightdata,
    clean_html_to_text,
    extract_headlines,
    summarize_with_anthropic_news_script,
    summarize_with_ollama
)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv()


class NewsScraper:
    _rate_limiter = AsyncLimiter(5, 1)  # 5 requests/second

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def scrape_news(self, topics: List[str]) -> Dict[str, str]:
        """Scrape and analyze news articles"""
        results = {}
        
        for topic in topics:
            async with self._rate_limiter:
                try:
                    logging.info(f"Generating URLs for topic: {topic}")
                    urls = generate_news_urls_to_scrape([topic])
                    logging.info(f"Generated URL: {urls[topic]}")

                    logging.info(f"Scraping with BrightData for topic: {topic}")
                    search_html = scrape_with_brightdata(urls[topic])
                    logging.info(f"BrightData HTML received (first 500 chars): {search_html[:500]}...") # Log part of HTML

                    logging.info(f"Cleaning HTML to text for topic: {topic}")
                    clean_text = clean_html_to_text(search_html)
                    logging.info(f"Cleaned text (first 500 chars): {clean_text[:500]}...") # Log part of cleaned text

                    logging.info(f"Extracting headlines for topic: {topic}")
                    headlines = extract_headlines(clean_text)
                    logging.info(f"Extracted headlines: \n{headlines}") # Log extracted headlines

                    logging.info(f"Summarizing with Anthropic for topic: {topic}")
                    summary = summarize_with_anthropic_news_script(
                        api_key=os.getenv("ANTHROPIC_API_KEY"),
                        headlines=headlines
                    )
                    logging.info(f"Summary from Anthropic (first 500 chars): {summary[:500]}...") # Log part of summary
                    results[topic] = summary
                except Exception as e:
                    logging.error(f"Error scraping news for topic {topic}: {e}", exc_info=True)
                    results[topic] = f"Error: {str(e)}"
                await asyncio.sleep(1) # Avoid overwhelming news sites

        return {"news_analysis" : results}


