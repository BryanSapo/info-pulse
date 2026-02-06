"""News fetcher module - Fetches news from RSS feeds and NewsAPI."""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse, parse_qs

import feedparser
import httpx
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a news article."""

    title: str
    link: str
    source: str
    published: datetime
    summary: str = ""
    ai_summary: str = ""
    topic: str = ""
    id: str = field(default="")

    def __post_init__(self):
        """Generate unique ID based on title and link."""
        if not self.id:
            content = f"{self.title}{self.link}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:12]


class NewsFetcher:
    """Fetches news from multiple RSS feeds and NewsAPI."""

    def __init__(
        self,
        topics_file: str = "topics.yaml",
        news_api_key: str | None = None,
    ):
        self.topics_file = topics_file
        self.news_api_key = news_api_key
        self.topics_config = self._load_topics()
        self.seen_ids: set[str] = set()

    def _load_topics(self) -> dict[str, Any]:
        """Load topics configuration from YAML file."""
        try:
            with open(self.topics_file, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Topics file not found: {self.topics_file}")
            return {"topics": [], "settings": {}}

    def _clean_google_news_url(self, url: str) -> str:
        """Extract the actual article URL from Google News redirect."""
        if "news.google.com" in url:
            # Try to extract from URL parameter
            parsed = urlparse(url)
            # Google News URLs are complex, return as-is for now
            # The actual URL is encoded in the path
            return url
        return url

    def _parse_published_date(self, entry: dict) -> datetime:
        """Parse published date from feed entry."""
        # Try different date fields
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if date_field in entry and entry[date_field]:
                try:
                    return datetime(*entry[date_field][:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue

        # Try parsing string dates
        for date_str_field in ["published", "updated", "created"]:
            if date_str_field in entry and entry[date_str_field]:
                try:
                    # Handle common date formats
                    date_str = entry[date_str_field]
                    # Remove timezone abbreviations
                    date_str = re.sub(r"\s+[A-Z]{3,4}$", "", date_str)
                    for fmt in [
                        "%a, %d %b %Y %H:%M:%S %z",
                        "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%SZ",
                        "%a, %d %b %Y %H:%M:%S",
                    ]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return dt
                        except ValueError:
                            continue
                except Exception:
                    continue

        # Default to now
        return datetime.now(timezone.utc)

    def _extract_summary(self, entry: dict) -> str:
        """Extract summary/description from feed entry."""
        for field in ["summary", "description", "content"]:
            if field in entry:
                content = entry[field]
                if isinstance(content, list) and content:
                    content = content[0].get("value", "")
                if content:
                    # Strip HTML tags
                    clean = re.sub(r"<[^>]+>", "", str(content))
                    # Limit length
                    return clean[:500] if len(clean) > 500 else clean
        return ""

    def fetch_rss_feed(
        self, feed_url: str, feed_name: str, topic_name: str
    ) -> list[Article]:
        """Fetch articles from a single RSS feed."""
        articles = []
        try:
            logger.info(f"Fetching RSS feed: {feed_name} ({feed_url})")
            feed = feedparser.parse(feed_url)

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {feed_name}: {feed.bozo_exception}")

            for entry in feed.entries[:20]:  # Limit to 20 entries per feed
                title = entry.get("title", "").strip()
                link = entry.get("link", "")

                if not title or not link:
                    continue

                # Clean Google News URLs
                link = self._clean_google_news_url(link)

                article = Article(
                    title=title,
                    link=link,
                    source=feed_name,
                    published=self._parse_published_date(entry),
                    summary=self._extract_summary(entry),
                    topic=topic_name,
                )

                # Deduplicate
                if article.id not in self.seen_ids:
                    self.seen_ids.add(article.id)
                    articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from {feed_name}")

        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_name}: {e}")

        return articles

    def fetch_news_api(
        self, keywords: list[str], topic_name: str
    ) -> list[Article]:
        """Fetch articles from NewsAPI as fallback."""
        if not self.news_api_key:
            logger.debug("NewsAPI key not configured, skipping")
            return []

        articles = []
        query = " OR ".join(keywords[:3])  # Limit query complexity

        try:
            logger.info(f"Fetching from NewsAPI for topic: {topic_name}")
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "apiKey": self.news_api_key,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 10,
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            for item in data.get("articles", []):
                title = item.get("title", "").strip()
                link = item.get("url", "")

                if not title or not link or title == "[Removed]":
                    continue

                # Parse date
                pub_date = datetime.now(timezone.utc)
                if item.get("publishedAt"):
                    try:
                        pub_date = datetime.fromisoformat(
                            item["publishedAt"].replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                article = Article(
                    title=title,
                    link=link,
                    source=item.get("source", {}).get("name", "NewsAPI"),
                    published=pub_date,
                    summary=item.get("description", "")[:500],
                    topic=topic_name,
                )

                if article.id not in self.seen_ids:
                    self.seen_ids.add(article.id)
                    articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from NewsAPI")

        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")

        return articles

    def fetch_all(self) -> dict[str, list[Article]]:
        """Fetch articles from all configured topics and sources."""
        settings = self.topics_config.get("settings", {})
        max_articles = settings.get("max_articles_per_topic", 10)
        keep_days = settings.get("keep_days", 2)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=keep_days)

        results: dict[str, list[Article]] = {}

        for topic in self.topics_config.get("topics", []):
            topic_name = topic.get("name", "Unknown")
            keywords = topic.get("keywords", [])
            rss_feeds = topic.get("rss_feeds", [])

            logger.info(f"Processing topic: {topic_name}")
            topic_articles: list[Article] = []

            # Fetch from RSS feeds
            for feed in rss_feeds:
                feed_url = feed.get("url", "")
                feed_name = feed.get("name", "Unknown")
                if feed_url:
                    articles = self.fetch_rss_feed(feed_url, feed_name, topic_name)
                    topic_articles.extend(articles)

            # Use NewsAPI as fallback if we have few articles
            if len(topic_articles) < 5 and keywords:
                api_articles = self.fetch_news_api(keywords, topic_name)
                topic_articles.extend(api_articles)

            # Filter by date and sort by published date
            topic_articles = [
                a for a in topic_articles if a.published >= cutoff_date
            ]
            topic_articles.sort(key=lambda x: x.published, reverse=True)

            # Limit articles per topic
            results[topic_name] = topic_articles[:max_articles]
            logger.info(f"Topic '{topic_name}': {len(results[topic_name])} articles")

        return results
