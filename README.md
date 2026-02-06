# Info Pulse 🏀

AI-powered Lakers & NBA news aggregator that automatically fetches, summarizes, and publishes news to GitHub Pages.

## Features

- **Automated News Fetching**: Collects news from multiple RSS feeds and NewsAPI every 2 hours
- **AI Summarization**: Uses OpenRouter API to generate concise summaries with key points
- **Lakers-Focused**: Pre-configured for Los Angeles Lakers news with NBA league coverage
- **GitHub Pages**: Static site auto-deployed to GitHub Pages
- **Easy Topic Management**: Edit `topics.yaml` via GitHub's web interface to customize topics

## Quick Start

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/info-pulse.git
cd info-pulse

# Install dependencies with uv
uv sync
```

### 2. Configure API Keys

Create a `.env` file based on the template:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
NEWS_API_KEY=your_newsapi_key_here  # Optional
```

Get your API keys:
- **OpenRouter**: https://openrouter.ai/keys (required for AI summarization)
- **NewsAPI**: https://newsapi.org/register (optional fallback)

### 3. Run Locally

```bash
# Run the full pipeline
uv run python main.py

# Skip AI summarization (for testing)
uv run python main.py --skip-summarize
```

The generated site will be in the `docs/` folder. Open `docs/index.html` in your browser.

## GitHub Actions Setup

### Add Repository Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

1. `OPENROUTER_API_KEY`: Your OpenRouter API key
2. `NEWS_API_KEY`: Your NewsAPI key (optional)

### Enable GitHub Pages

1. Go to repo → Settings → Pages
2. Source: "GitHub Actions"
3. The workflow will automatically deploy on push and every 2 hours

## Customize Topics

Edit `topics.yaml` directly in GitHub's web interface (click the pencil icon):

```yaml
topics:
  - name: "Lakers News"
    description: "Los Angeles Lakers team news"
    keywords:
      - "Lakers"
      - "Los Angeles Lakers"
    rss_feeds:
      - url: "https://www.silverscreenandroll.com/rss/current.xml"
        name: "Silver Screen and Roll"
      # Add more feeds here
```

Changes trigger an automatic rebuild within minutes.

## Project Structure

```
info-pulse/
├── .github/
│   └── workflows/
│       └── fetch-news.yml    # GitHub Actions workflow
├── src/
│   └── info_pulse/
│       ├── __init__.py
│       ├── news_fetcher.py   # RSS/API news fetching
│       ├── summarizer.py     # OpenRouter AI summarization
│       └── site_generator.py # Static HTML generation
├── templates/
│   └── index.html.jinja      # Site template
├── docs/                     # Generated site (GitHub Pages)
├── topics.yaml               # Topic configuration
├── main.py                   # Entry point
├── pyproject.toml            # Dependencies
├── .env.example              # Environment template
└── .gitignore
```

## Command Line Options

```bash
uv run python main.py --help

Options:
  --topics-file PATH    Path to topics config (default: topics.yaml)
  --output-dir PATH     Output directory (default: docs)
  --templates-dir PATH  Templates directory (default: templates)
  --skip-summarize      Skip AI summarization
  --model MODEL         OpenRouter model (default: google/gemini-2.0-flash-001)
```

## RSS Feeds Included

### Lakers-Specific
- Silver Screen and Roll (SB Nation)
- Lakers Nation
- Reddit r/lakers
- Google News - Lakers

### NBA League
- ESPN NBA
- Yahoo Sports NBA
- CBS Sports NBA
- Reddit r/nba

## License

MIT License - feel free to fork and customize!

---

**Go Lakers! 💜💛**
