def main():
    """Info Pulse - Lakers & NBA News Aggregator

Main entry point for the news aggregation pipeline:
1. Fetch news from RSS feeds and NewsAPI
2. Summarize articles using OpenRouter AI
3. Generate static HTML for GitHub Pages
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    """Run the news aggregation pipeline."""
    parser = argparse.ArgumentParser(description="Info Pulse - Lakers & NBA News Aggregator")
    parser.add_argument(
        "--topics-file",
        default="topics.yaml",
        help="Path to topics configuration file (default: topics.yaml)",
    )
    parser.add_argument(
        "--output-dir",
        default="docs",
        help="Output directory for generated site (default: docs)",
    )
    parser.add_argument(
        "--templates-dir",
        default="templates",
        help="Templates directory (default: templates)",
    )
    parser.add_argument(
        "--skip-summarize",
        action="store_true",
        help="Skip AI summarization (useful for testing)",
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-oss-120b:free",
        help="OpenRouter model to use (default: openai/gpt-oss-120b:free)",
    )
    args = parser.parse_args()

    # Get API keys from environment
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    news_api_key = os.getenv("NEWS_API_KEY")

    if not openrouter_api_key and not args.skip_summarize:
        logger.error("OPENROUTER_API_KEY environment variable is required")
        logger.error("Set it in .env file or export it: export OPENROUTER_API_KEY=your_key")
        sys.exit(1)

    # Import here to avoid issues if dependencies aren't installed
    from info_pulse.news_fetcher import NewsFetcher
    from info_pulse.summarizer import Summarizer
    from info_pulse.site_generator import SiteGenerator

    # Step 1: Fetch news
    logger.info("=" * 50)
    logger.info("Step 1: Fetching news from RSS feeds and APIs")
    logger.info("=" * 50)

    fetcher = NewsFetcher(
        topics_file=args.topics_file,
        news_api_key=news_api_key,
    )
    articles_by_topic = fetcher.fetch_all()

    total_articles = sum(len(articles) for articles in articles_by_topic.values())
    logger.info(f"Fetched {total_articles} articles across {len(articles_by_topic)} topics")

    if total_articles == 0:
        logger.warning("No articles fetched. Check your RSS feeds and API keys.")

    # Step 2: Summarize with AI
    if args.skip_summarize:
        logger.info("=" * 50)
        logger.info("Step 2: Skipping AI summarization (--skip-summarize)")
        logger.info("=" * 50)

        # Convert articles to SummarizedArticle format without AI
        from info_pulse.summarizer import SummarizedArticle

        summarized_by_topic = {}
        for topic, articles in articles_by_topic.items():
            summarized_by_topic[topic] = [
                SummarizedArticle(
                    original=article,
                    ai_title=article.title,
                    ai_summary=article.summary,
                    key_points=[],
                )
                for article in articles
            ]
    else:
        logger.info("=" * 50)
        logger.info("Step 2: Summarizing articles with AI")
        logger.info("=" * 50)

        summarizer = Summarizer(
            api_key=openrouter_api_key,
            model=args.model,
        )
        summarized_by_topic = summarizer.summarize_all(articles_by_topic)

    # Step 3: Generate static site
    logger.info("=" * 50)
    logger.info("Step 3: Generating static site")
    logger.info("=" * 50)

    generator = SiteGenerator(
        output_dir=args.output_dir,
        templates_dir=args.templates_dir,
    )
    generator.generate(summarized_by_topic)

    logger.info("=" * 50)
    logger.info("✅ Pipeline complete!")
    logger.info(f"   Site generated at: {args.output_dir}/index.html")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
