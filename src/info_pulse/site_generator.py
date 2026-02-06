"""Site generator module - Generates static HTML for GitHub Pages."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from info_pulse.summarizer import SummarizedArticle

logger = logging.getLogger(__name__)


class SiteGenerator:
    """Generates static HTML site from summarized articles."""

    def __init__(
        self,
        output_dir: str = "docs",
        templates_dir: str = "templates",
    ):
        self.output_dir = Path(output_dir)
        self.templates_dir = Path(templates_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True,
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date
        self.env.filters["time_ago"] = self._time_ago

    def _format_date(self, dt: datetime) -> str:
        """Format datetime for display."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                return dt
        return dt.strftime("%b %d, %Y at %I:%M %p")

    def _time_ago(self, dt: datetime) -> str:
        """Get human-readable time ago string."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                return "recently"

        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} min ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        else:
            days = int(seconds / 86400)
            return f"{days}d ago"

    def _articles_to_json(
        self, articles_by_topic: dict[str, list[SummarizedArticle]]
    ) -> list[dict]:
        """Convert articles to JSON-serializable format."""
        data = []
        for topic, articles in articles_by_topic.items():
            topic_data = {
                "name": topic,
                "articles": [],
            }
            for article in articles:
                topic_data["articles"].append(
                    {
                        "id": article.original.id,
                        "title": article.ai_title,
                        "original_title": article.original.title,
                        "summary": article.ai_summary,
                        "key_points": article.key_points,
                        "link": article.original.link,
                        "source": article.original.source,
                        "published": article.original.published.isoformat(),
                        "topic": topic,
                    }
                )
            data.append(topic_data)
        return data

    def generate(
        self,
        articles_by_topic: dict[str, list[SummarizedArticle]],
        site_title: str = "Info Pulse - Lakers News",
    ) -> None:
        """Generate the static site."""
        logger.info("Generating static site...")

        # Generate timestamp
        generated_at = datetime.now(timezone.utc)

        # Count total articles
        total_articles = sum(len(articles) for articles in articles_by_topic.values())

        # Render index.html
        try:
            template = self.env.get_template("index.html.jinja")
            html = template.render(
                site_title=site_title,
                topics=articles_by_topic,
                generated_at=generated_at,
                total_articles=total_articles,
            )

            index_path = self.output_dir / "index.html"
            index_path.write_text(html, encoding="utf-8")
            logger.info(f"Generated {index_path}")
        except Exception as e:
            logger.error(f"Error generating index.html: {e}")
            raise

        # Generate news.json for potential client-side use
        json_data = {
            "generated_at": generated_at.isoformat(),
            "total_articles": total_articles,
            "topics": self._articles_to_json(articles_by_topic),
        }

        json_path = self.output_dir / "news.json"
        json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        logger.info(f"Generated {json_path}")

        # Copy static assets if they exist
        self._copy_static_assets()

        logger.info(f"Site generation complete! {total_articles} articles across {len(articles_by_topic)} topics")

    def _copy_static_assets(self) -> None:
        """Copy static CSS/JS files to output directory."""
        # CSS is embedded in template, but we can have an external file too
        static_dir = self.templates_dir / "static"
        if static_dir.exists():
            import shutil

            dest_static = self.output_dir / "static"
            if dest_static.exists():
                shutil.rmtree(dest_static)
            shutil.copytree(static_dir, dest_static)
            logger.info("Copied static assets")
