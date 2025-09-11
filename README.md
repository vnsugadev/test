# Reddit Ban Tracker Bot

A Python bot that uses PRAW (Python Reddit API Wrapper) to fetch and track bans from Reddit subreddits. The bot maintains a history of previously seen bans and displays only newly discovered ones.

## Features

- 🔍 Fetches ban information from Reddit using PRAW
- 💾 Stores previously seen bans in JSON format
- 🆕 Identifies and displays only new bans
- 🛡️ Robust error handling and logging
- ⚙️ Configurable via environment variables
- 📝 Comprehensive logging to both file and console

## Prerequisites

- Python 3.7 or higher
- Reddit API credentials (Client ID, Client Secret)
- pip (Python package installer)

## Installation

1. **Clone the repository** (or download the files):
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Reddit API credentials**:
   - Go to https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Choose "script" as the app type
   - Note down your Client ID and Client Secret

4. **Create a `.env` file** in the project directory:
   ```bash
   touch .env
   ```

5. **Add your Reddit credentials to `.env`**:
   ```env
   REDDIT_CLIENT_ID=your_client_id_here
   REDDIT_CLIENT_SECRET=your_client_secret_here
   REDDIT_USER_AGENT=RedditBanTracker/1.0 by YourUsername
   ```

## Usage

### Basic Usage

Run the bot with default subreddits:
```bash
python reddit_ban_tracker.py
```

### Enhanced CLI Usage

For more control, use the enhanced CLI interface:
```bash
python cli.py --help
```

#### CLI Examples

```bash
# Monitor default subreddits
python cli.py

# Monitor specific subreddits
python cli.py -s "announcements,help,askreddit"

# Set custom fetch limit
python cli.py --limit 100

# Use custom config and storage files
python cli.py --config mybot.env --storage my_bans.json

# Monitor askreddit with custom limit
python cli.py --subreddits askreddit --limit 50
```

### Basic Script Usage

Alternatively, use the basic script directly:
```bash
python reddit_ban_tracker.py "subreddit1,subreddit2,subreddit3"
```

## Configuration

The bot can be configured through the `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| `REDDIT_CLIENT_ID` | Yes | Your Reddit app's Client ID |
| `REDDIT_CLIENT_SECRET` | Yes | Your Reddit app's Client Secret |
| `REDDIT_USER_AGENT` | Yes | User agent string for API requests |

## Files Created

The bot creates several files during operation:

- **`banned_users.json`**: Stores the history of seen bans
- **`reddit_ban_tracker.log`**: Log file with detailed operation history

## How It Works

1. **Authentication**: Connects to Reddit API using PRAW with your credentials
2. **Data Fetching**: Attempts to fetch ban data from specified subreddits
3. **Storage**: Loads previously seen bans from `banned_users.json`
4. **Comparison**: Compares new data with stored data to identify new bans
5. **Display**: Shows only the newly discovered bans
6. **Update**: Saves updated ban data back to the JSON file

## Important Notes

### Permissions

- **Ban Lists**: Accessing actual ban lists requires moderator permissions for the subreddit
- **Public Data**: If ban lists aren't accessible, the bot falls back to publicly available moderation log data
- **Rate Limits**: The bot respects Reddit's API rate limits automatically through PRAW

### Privacy and Ethics

- This bot only accesses publicly available information or data you have permission to access
- Ban information is stored locally and not shared
- Use responsibly and in compliance with Reddit's Terms of Service

## Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Ensure your `.env` file exists and contains all required variables
   - Check that variable names are spelled correctly

2. **"Cannot access ban list"**
   - This is normal if you don't have moderator permissions
   - The bot will fall back to publicly available moderation data

3. **"Error fetching from subreddit"**
   - Check that the subreddit name is spelled correctly
   - Ensure the subreddit exists and is accessible

### Debugging

Enable detailed logging by checking the `reddit_ban_tracker.log` file:
```bash
tail -f reddit_ban_tracker.log
```

## Example Output

```
==================================================
NEW BANS DETECTED: 2
==================================================

Subreddit: r/announcements
Action: banuser
Target: u/example_user1
Details: Spam violation
Moderator: AutoModerator
Date: 2024-01-15 14:30:25
------------------------------

Subreddit: r/help
Action: removepost
Target: u/example_user2
Details: Rule violation
Moderator: ModeratorName
Date: 2024-01-15 14:32:10
------------------------------
```

## Development

### Project Structure

```
.
├── reddit_ban_tracker.py    # Main bot script
├── cli.py                  # Enhanced CLI interface
├── test_bot.py             # Test script for verification
├── requirements.txt         # Python dependencies
├── .env                    # Configuration file (create this)
├── .env.example            # Configuration template
├── banned_users.json       # Ban history (created automatically)
├── reddit_ban_tracker.log  # Log file (created automatically)
└── README.md              # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and monitoring purposes only. Users are responsible for complying with Reddit's Terms of Service and API guidelines. The bot should be used responsibly and ethically.