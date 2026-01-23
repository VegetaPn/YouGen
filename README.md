# YouGen - X/Twitter Growth Automation

A semi-automated tool to grow your X/Twitter followers by commenting on influencer tweets.

[中文文档](README_CN.md)

## Background

Hey everyone! I have a dream – to become a certified Meme Lord 🎭.

To achieve this noble goal, I used to spend hours every day scrolling through Twitter, hunting for viral tweets, and practicing my witty comments. But here's the problem: this approach is incredibly inefficient, and writing comments by myself doesn't really help me improve. I was stuck in a loop, never getting closer to becoming a true Meme Master.

So I thought, why not build a tool to help me? That's how **YouGen** (有梗, meaning "having memes/jokes" in Chinese) was born – an AI-powered assistant that:
- Automatically discovers trending tweets
- Generates witty comments using Claude Opus 4.5
- Helps me learn by reviewing and refining AI-generated content
- Lets me focus on the creative part while handling the tedious work

The initial version is now complete and **open-sourced**. Whether you're aspiring to be a Meme Lord like me, or just want to grow your Twitter presence more efficiently, feel free to use it!

## Features

- 🤖 AI-powered comment generation using Claude Opus 4.5
- 📊 Trend analysis: Automatically filter trending tweets
- ✋ Semi-automated: Human review before publishing
- 🎯 Smart deduplication: Avoid commenting on the same author repeatedly
- 💾 Lightweight storage: JSON-based file storage, no database required

## Prerequisites

1. **bird CLI** - X/Twitter command-line tool
   ```bash
   brew install steipete/tap/bird
   bird login
   ```

2. **Python 3.10+** and dependencies
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. **Claude API Key**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```

## Quick Start

### 1. Configure Influencers

Edit `yougen/config/influencers.yaml`:

```yaml
influencers:
  - username: "example_user"
    user_id: ""           # Optional, leave empty
    priority: "high"      # high, medium, low
    check_interval: 15    # Check interval in minutes
    topics: ["AI", "Tech"]
```

**Note**: The `user_id` field is optional and can be left empty. After modifying `influencers.yaml`, the program will automatically reload the configuration on the next `scan` command by comparing file modification times.

### 2. Configure Your Profile

Edit `yougen/config/user_profile.yaml` to customize your comment style.

### 3. Run the Workflow

```bash
# 1. Check authentication
python main.py auth

# 2. Scan tweets and generate comments
python main.py scan

# 3. Review comments (interactive)
python main.py review

# 4. Publish approved comments
python main.py publish

# 5. View statistics
python main.py stats
```

## Command Reference

### `python main.py scan`
Scan influencer tweets, analyze trends, and generate comments.

- Only collects tweets from the last 30 minutes
- Ranks by trending score
- Generates up to 10 comments per scan
- Comments are saved with `pending` status

### `python main.py review`
Interactive review of pending comments.

Available actions:
- `[p]` Publish now - Publish immediately
- `[a]` Approve - Approve for later publication
- `[r]` Refine - Optimize comment (uses Agent session memory)
- `[s]` Skip - Skip this comment
- `[q]` Quit - Exit review mode

### `python main.py publish`
Batch publish all approved comments.

### `python main.py stats`
Display statistics:
- Comment status distribution
- Recent publication count
- Influencer list

## Directory Structure

```
yougen/
├── config/               # Configuration files
│   ├── user_profile.yaml  # User profile
│   ├── influencers.yaml   # Influencer list
│   └── settings.yaml      # System settings
├── core/                 # Core modules
│   ├── bird_client.py     # bird CLI wrapper
│   ├── browser_client.py  # Browser automation client
│   ├── tweet_collector.py # Tweet collection
│   ├── trend_analyzer.py  # Trend analysis
│   └── comment_generator.py # Comment generation
├── storage/              # Storage modules
│   ├── models.py          # Data models
│   └── file_store.py      # JSON storage
├── cli/                  # CLI modules
│   ├── main.py            # Main entry point
│   └── reviewer.py        # Interactive review
└── data/                 # Data directory
    ├── influencers/       # Influencer data
    ├── tweets/            # Tweets (by date)
    └── comments/          # Comments (by status)
        ├── pending/
        ├── approved/
        ├── rejected/
        └── published/
```

## How It Works

### 1. Tweet Collection
- Fetches latest tweets from configured influencers
- Filters tweets from the last 30 minutes
- Deduplicates: Excludes processed tweets and authors commented on in the last 24 hours

### 2. Trend Analysis
Calculates trending score (0-100):
```
Weighted Engagement = Likes×1.0 + Retweets×2.0 + Replies×1.5
Engagement Rate per Minute = Weighted Engagement / Tweet Age (minutes)
Trending Score = min(Engagement Rate / 5 × 50, 100)
```

Filter rules:
- Default threshold: 60 points
- Protection logic: Keeps at least 3 tweets

### 3. Comment Generation
Uses Claude Agent SDK:
- Model: Claude Opus 4.5
- System prompt: Injects user profile and style examples
- Session memory: Supports multi-round refinement
- **Language matching**: Automatically generates comments in the same language as the tweet

### 4. Human Review
Interactive CLI:
- Shows tweet context and engagement metrics
- Previews generated comments
- Supports real-time refinement (using session context)
- Can publish immediately or approve for batch publishing

## Configuration

### settings.yaml
```yaml
collection:
  max_tweet_age_minutes: 30    # Maximum tweet age
  max_tweets_per_scan: 10      # Max tweets per scan

trend_analysis:
  min_score: 60.0              # Minimum trending score
  like_weight: 1.0             # Like weight
  retweet_weight: 2.0          # Retweet weight
  reply_weight: 1.5            # Reply weight

rate_limit:
  delay_seconds: 2.0           # bird CLI request interval
  max_concurrent_generations: 3 # Max concurrent generations
```

## Best Practices

1. **Authentication Management**
   - Ensure `bird login` is working properly
   - Regularly run `python main.py auth` to check status

2. **Comment Style**
   - Add real comment examples in `user_profile.yaml`
   - Keep style consistent: engaging but professional

3. **Publishing Frequency**
   - Avoid publishing too many comments in a short time
   - Use `python main.py stats` to monitor publishing frequency

4. **Influencer Management**
   - Adjust `priority` and `check_interval` based on quality
   - Regularly review and update your influencer list

5. **Trending Score Tuning**
   - Adjust `min_score` based on actual results
   - Adjust weights to match your target audience

## Troubleshooting

### bird CLI Authentication Failed
```bash
bird logout
bird login
```

### Claude API Error
Check API key and base URL:
```bash
echo $ANTHROPIC_API_KEY
echo $ANTHROPIC_BASE_URL  # If using custom endpoint
```

### Import Error
Make sure to run from project root:
```bash
cd /path/to/YouGen
python main.py scan
```

### Tweet Filter Too Strict
Lower the `min_score` in `settings.yaml`, or increase `max_tweet_age_minutes`.

## 🔑 Twitter Login Setup (Important)

**Recommended: Use Real Chrome Browser (Headless Mode, runs in background)**

### First Time Setup

```bash
# 1. Start Chrome with window (needed for first login)
./start_chrome.sh --show-window

# 2. Manually log in to Twitter in the Chrome window

# 3. After login, switch to background mode (no window)
./stop_chrome.sh
./start_chrome.sh

# 4. Use normally
python main.py publish
```

### Daily Usage

```bash
# 1. Start Chrome (runs in background, no window)
./start_chrome.sh

# 2. Use normally
python main.py review
```

See [SETUP_TWITTER_REAL_CHROME.md](doc/SETUP_TWITTER_REAL_CHROME.md) for details.

### How It Works
- Uses real Chrome browser in Headless mode (`--headless=new`)
- Chrome runs in background, **no window shown, doesn't interfere with your work**
- agent-browser connects via CDP (Chrome DevTools Protocol)
- Twitter sees a normal Chrome browser, won't detect automation
- Login state saved in `~/.argo/chrome-profile/`
- Can switch to window mode for debugging

### Why Use Browser Instead of bird CLI?

Since bird CLI is easily detected by Twitter as automation (HTTP 403 errors), the system defaults to using **agent-browser** to simulate real browser operations for publishing comments.

**Advantages:**
- ✅ **Simulates real user behavior** - Uses real browser, not detected as API calls
- ✅ **Maintains login state** - Keeps session through cookies
- ✅ **Supports complex interactions** - Handles frontend logic
- ✅ **Avoids rate limiting** - Doesn't trigger API rate limits

### Alternative (Not Recommended)

If you want to use agent-browser's automation mode (may be detected by Twitter):

```bash
# Disable CDP mode
python main.py publish --no-cdp
```

See [SETUP_TWITTER_LOGIN.md](doc/SETUP_TWITTER_LOGIN.md) (may encounter "unsafe browser" errors)

## Development

### Import Convention
Use absolute imports:
```python
from yougen.storage.models import Tweet
from yougen.core.bird_client import BirdClient
```

### Running Tests
```bash
pytest tests/
```

## Configuration Management

### Auto-reload Influencers

The program automatically detects changes to `influencers.yaml`:

1. **First run**: Loads from `influencers.yaml`, saves to `data/influencers/managed.json`
2. **Subsequent runs**: Compares file modification times
   - If YAML is newer than JSON → Automatically reloads ✅
   - If YAML is unchanged → Uses existing JSON

This means:
- ✅ Just modify `influencers.yaml` and run, no need to manually delete JSON
- ✅ Manual changes to `managed.json` (not recommended) won't be overwritten
- ⚠️  Always modify the YAML config file, don't edit JSON directly

### Language Matching

The comment generator automatically detects tweet language and replies in the same language:

- Tweet in English → Comment in English
- Tweet in Chinese → Comment in Chinese
- Tweet in Japanese → Comment in Japanese

This is implemented by explicitly instructing Claude to match the language in the system prompt.

## License

MIT
