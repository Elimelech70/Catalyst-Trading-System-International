"""
News and sentiment analysis for the Catalyst Trading Agent.

This module provides:
- News fetching for HKEX stocks
- Sentiment analysis using simple NLP
- News filtering and ranking
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


@dataclass
class NewsItem:
    """A news article."""

    headline: str
    source: str
    url: str
    published_at: datetime
    sentiment_score: float  # -1 to 1
    summary: str | None = None


class NewsClient:
    """News fetching and sentiment analysis."""

    # Positive sentiment keywords (financial context)
    POSITIVE_WORDS = {
        "surge",
        "soar",
        "rally",
        "gain",
        "rise",
        "jump",
        "climb",
        "boost",
        "growth",
        "profit",
        "beat",
        "exceed",
        "upgrade",
        "buy",
        "strong",
        "bullish",
        "outperform",
        "success",
        "record",
        "high",
        "positive",
        "optimistic",
        "expansion",
        "improve",
        "revenue",
        "dividend",
        "acquire",
        "partnership",
        "breakthrough",
        "innovation",
    }

    # Negative sentiment keywords
    NEGATIVE_WORDS = {
        "fall",
        "drop",
        "decline",
        "plunge",
        "crash",
        "slump",
        "loss",
        "miss",
        "downgrade",
        "sell",
        "weak",
        "bearish",
        "underperform",
        "fail",
        "low",
        "negative",
        "pessimistic",
        "contraction",
        "worsen",
        "debt",
        "lawsuit",
        "investigation",
        "scandal",
        "fraud",
        "layoff",
        "resign",
        "warning",
        "concern",
        "risk",
        "uncertainty",
    }

    # Stock code to company name mapping for major HKEX stocks
    STOCK_NAMES = {
        "0700": "Tencent",
        "9988": "Alibaba",
        "0005": "HSBC",
        "0941": "China Mobile",
        "0939": "CCB",
        "1398": "ICBC",
        "2318": "Ping An",
        "3988": "Bank of China",
        "0883": "CNOOC",
        "0388": "HK Exchanges",
        "1299": "AIA",
        "2628": "China Life",
        "0011": "Hang Seng Bank",
        "0016": "SHK Properties",
        "0001": "CKH Holdings",
        "0027": "Galaxy Entertainment",
        "0066": "MTR Corporation",
        "0002": "CLP Holdings",
        "0003": "HK & China Gas",
        "0006": "Power Assets",
        "0012": "Henderson Land",
        "0017": "New World Development",
        "0267": "CITIC",
        "0386": "Sinopec",
        "0688": "China Overseas Land",
        "0762": "China Unicom",
        "0823": "Link REIT",
        "0857": "PetroChina",
        "0960": "Longfor",
        "0968": "Xinyi Solar",
        "1038": "CK Infrastructure",
        "1044": "Hengan",
        "1093": "CSPC Pharma",
        "1109": "China Resources Land",
        "1113": "CK Asset",
        "1177": "Sino Biopharm",
        "1211": "BYD",
        "1810": "Xiaomi",
        "1929": "Chow Tai Fook",
        "1997": "Wharf REIC",
        "2007": "Country Garden",
        "2020": "ANTA Sports",
        "2269": "WuXi Bio",
        "2313": "Shenzhou",
        "2319": "Mengniu",
        "2382": "Sunny Optical",
        "3690": "Meituan",
        "9618": "JD.com",
        "9888": "Baidu",
        "9999": "NetEase",
    }

    def __init__(self, api_key: str | None = None):
        """Initialize news client.

        Args:
            api_key: News API key (optional, uses NEWSAPI_KEY env var)
        """
        self.api_key = api_key or os.environ.get("NEWSAPI_KEY")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CatalystTradingAgent/1.0"})

    def get_news(
        self, symbol: str, hours: int = 24, limit: int = 10
    ) -> dict:
        """Get news and sentiment for a symbol.

        Args:
            symbol: HKEX stock code
            hours: Hours to look back
            limit: Maximum news items

        Returns:
            Dict with news items and overall sentiment
        """
        # Get company name for search
        company_name = self.STOCK_NAMES.get(symbol, symbol)

        # Fetch news from multiple sources
        news_items = []

        # Try NewsAPI if we have a key
        if self.api_key:
            try:
                newsapi_items = self._fetch_newsapi(company_name, hours)
                news_items.extend(newsapi_items)
            except Exception as e:
                logger.warning(f"NewsAPI fetch failed: {e}")

        # Always try RSS feeds (no API key needed)
        try:
            rss_items = self._fetch_rss_feeds(company_name, symbol, hours)
            news_items.extend(rss_items)
        except Exception as e:
            logger.warning(f"RSS fetch failed: {e}")

        # Deduplicate by headline
        seen_headlines = set()
        unique_items = []
        for item in news_items:
            headline_key = item["headline"].lower()[:50]
            if headline_key not in seen_headlines:
                seen_headlines.add(headline_key)
                unique_items.append(item)

        # Sort by recency
        unique_items.sort(key=lambda x: x["published_at"], reverse=True)

        # Limit results
        unique_items = unique_items[:limit]

        # Calculate overall sentiment
        if unique_items:
            sentiments = [item["sentiment_score"] for item in unique_items]
            overall_sentiment = sum(sentiments) / len(sentiments)
        else:
            overall_sentiment = 0.0

        return {
            "symbol": symbol,
            "company_name": company_name,
            "news_count": len(unique_items),
            "overall_sentiment": round(overall_sentiment, 2),
            "sentiment_label": self._sentiment_label(overall_sentiment),
            "news": unique_items,
            "lookback_hours": hours,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _fetch_newsapi(self, query: str, hours: int) -> list[dict]:
        """Fetch news from NewsAPI."""
        if not self.api_key:
            return []

        from_date = datetime.now(HK_TZ) - timedelta(hours=hours)

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f'"{query}" OR "Hong Kong stock"',
            "from": from_date.isoformat(),
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": self.api_key,
            "pageSize": 20,
        }

        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = []
        for article in data.get("articles", []):
            headline = article.get("title", "")
            if not headline:
                continue

            items.append(
                {
                    "headline": headline,
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "sentiment_score": self._analyze_sentiment(
                        headline + " " + (article.get("description") or "")
                    ),
                    "summary": article.get("description"),
                }
            )

        return items

    def _fetch_rss_feeds(self, company_name: str, symbol: str, hours: int) -> list[dict]:
        """Fetch news from RSS feeds."""
        items = []
        cutoff = datetime.now(HK_TZ) - timedelta(hours=hours)

        # Hong Kong financial news RSS feeds
        feeds = [
            (
                "SCMP Business",
                "https://www.scmp.com/rss/91/feed",
            ),
            (
                "HKEJ",
                "https://www.hkej.com/rss/index.xml",
            ),
        ]

        for source_name, feed_url in feeds:
            try:
                response = self.session.get(feed_url, timeout=10)
                if response.status_code != 200:
                    continue

                # Simple RSS parsing without external library
                items.extend(
                    self._parse_rss(
                        response.text, source_name, company_name, symbol, cutoff
                    )
                )
            except Exception as e:
                logger.debug(f"RSS feed {source_name} failed: {e}")
                continue

        return items

    def _parse_rss(
        self,
        xml_content: str,
        source: str,
        company_name: str,
        symbol: str,
        cutoff: datetime,
    ) -> list[dict]:
        """Parse RSS XML content."""
        items = []

        # Simple regex-based XML parsing
        item_pattern = re.compile(r"<item>(.*?)</item>", re.DOTALL)
        title_pattern = re.compile(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>")
        link_pattern = re.compile(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>")
        pubdate_pattern = re.compile(r"<pubDate>(.*?)</pubDate>")
        desc_pattern = re.compile(
            r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", re.DOTALL
        )

        for item_match in item_pattern.finditer(xml_content):
            item_xml = item_match.group(1)

            title_match = title_pattern.search(item_xml)
            link_match = link_pattern.search(item_xml)
            pubdate_match = pubdate_pattern.search(item_xml)
            desc_match = desc_pattern.search(item_xml)

            if not title_match:
                continue

            headline = title_match.group(1).strip()

            # Filter for relevant news
            search_terms = [company_name.lower(), symbol]
            content = (headline + " " + (desc_match.group(1) if desc_match else "")).lower()

            if not any(term.lower() in content for term in search_terms):
                continue

            # Parse date
            pub_date = datetime.now(HK_TZ)
            if pubdate_match:
                try:
                    from email.utils import parsedate_to_datetime

                    pub_date = parsedate_to_datetime(pubdate_match.group(1))
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=HK_TZ)
                except Exception:
                    pass

            if pub_date < cutoff:
                continue

            items.append(
                {
                    "headline": headline,
                    "source": source,
                    "url": link_match.group(1).strip() if link_match else "",
                    "published_at": pub_date.isoformat(),
                    "sentiment_score": self._analyze_sentiment(
                        headline + " " + (desc_match.group(1) if desc_match else "")
                    ),
                    "summary": desc_match.group(1).strip()[:200] if desc_match else None,
                }
            )

        return items

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text.

        Returns score from -1 (very negative) to 1 (very positive).
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        # Score from -1 to 1
        score = (positive_count - negative_count) / total

        # Dampen extreme scores
        return max(-0.9, min(0.9, score))

    def _sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score >= 0.3:
            return "positive"
        elif score <= -0.3:
            return "negative"
        else:
            return "neutral"

    def has_catalyst(self, symbol: str, hours: int = 24) -> tuple[bool, str]:
        """Check if symbol has a news catalyst.

        Args:
            symbol: Stock code
            hours: Hours to look back

        Returns:
            (has_catalyst, reason)
        """
        news = self.get_news(symbol, hours=hours, limit=5)

        if news["news_count"] == 0:
            return False, "No recent news found"

        if news["overall_sentiment"] < 0.3:
            return False, f"Sentiment too low ({news['overall_sentiment']:.2f})"

        # Has positive news
        top_headline = news["news"][0]["headline"] if news["news"] else ""
        return True, f"Positive catalyst: {top_headline[:50]}..."


# Singleton instance
_news_client: NewsClient | None = None


def get_news_client(api_key: str | None = None) -> NewsClient:
    """Get or create news client singleton."""
    global _news_client
    if _news_client is None:
        _news_client = NewsClient(api_key)
    return _news_client
