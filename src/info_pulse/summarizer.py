"""Summarizer module - AI-powered news summarization using OpenRouter API."""

import logging
from dataclasses import dataclass

from openai import OpenAI

from info_pulse.news_fetcher import Article

logger = logging.getLogger(__name__)


@dataclass
class SummarizedArticle:
    """Article with AI-generated summary."""

    original: Article
    ai_title: str
    ai_summary: str
    key_points: list[str]


class Summarizer:
    """Summarizes news articles using OpenRouter API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b:free",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    def _create_prompt(self, articles: list[Article]) -> str:
        """Create a prompt for batch summarization."""
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"""
Article {i}:
Title: {article.title}
Source: {article.source}
Summary: {article.summary[:300] if article.summary else 'No summary available'}
---
"""
        return f"""You are a sports news analyst specializing in NBA basketball, particularly the Los Angeles Lakers.

Summarize the following news articles. For each article, provide:
1. A concise, engaging title (keep original if already good)
2. A 2-3 sentence summary highlighting the key points
3. 2-3 bullet points with the most important takeaways

Focus on facts, avoid speculation, and maintain a neutral tone.

{articles_text}

Respond in JSON format:
{{
  "articles": [
    {{
      "index": 1,
      "title": "Concise title",
      "summary": "2-3 sentence summary",
      "key_points": ["Point 1", "Point 2", "Point 3"]
    }}
  ]
}}
"""

    def summarize_batch(
        self, articles: list[Article], batch_size: int = 5
    ) -> list[SummarizedArticle]:
        """Summarize a batch of articles using OpenRouter API."""
        if not articles:
            return []

        summarized: list[SummarizedArticle] = []

        # Process in batches to avoid token limits
        for i in range(0, len(articles), batch_size):
            batch = articles[i : i + batch_size]
            logger.info(f"Summarizing batch {i // batch_size + 1} ({len(batch)} articles)")

            try:
                prompt = self._create_prompt(batch)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful sports news analyst. Always respond with valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                if content:
                    import json

                    try:
                        data = json.loads(content)
                        for item in data.get("articles", []):
                            idx = item.get("index", 1) - 1
                            if 0 <= idx < len(batch):
                                summarized.append(
                                    SummarizedArticle(
                                        original=batch[idx],
                                        ai_title=item.get("title", batch[idx].title),
                                        ai_summary=item.get("summary", ""),
                                        key_points=item.get("key_points", []),
                                    )
                                )
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        # Fallback: return articles without AI summary
                        for article in batch:
                            summarized.append(
                                SummarizedArticle(
                                    original=article,
                                    ai_title=article.title,
                                    ai_summary=article.summary,
                                    key_points=[],
                                )
                            )

            except Exception as e:
                logger.error(f"Error calling OpenRouter API: {e}")
                # Fallback: return articles without AI summary
                for article in batch:
                    summarized.append(
                        SummarizedArticle(
                            original=article,
                            ai_title=article.title,
                            ai_summary=article.summary,
                            key_points=[],
                        )
                    )

        return summarized

    def summarize_all(
        self, articles_by_topic: dict[str, list[Article]]
    ) -> dict[str, list[SummarizedArticle]]:
        """Summarize all articles grouped by topic."""
        results: dict[str, list[SummarizedArticle]] = {}

        for topic, articles in articles_by_topic.items():
            logger.info(f"Summarizing {len(articles)} articles for topic: {topic}")
            results[topic] = self.summarize_batch(articles)

        return results
