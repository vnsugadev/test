#!/usr/bin/env python3
"""
Reddit Ban Tracker Bot - Command Line Interface

Enhanced version with proper argument parsing and configuration options.
"""

import argparse
import sys
from reddit_ban_tracker import RedditBanTracker


def create_parser():
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Reddit Ban Tracker - Monitor and track bans from Reddit subreddits',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Monitor default subreddits
  %(prog)s -s announcements,help,reddit      # Monitor specific subreddits  
  %(prog)s --limit 100                       # Fetch up to 100 entries
  %(prog)s --config mybot.env                # Use custom config file
  %(prog)s --storage my_bans.json            # Use custom storage file
  %(prog)s --subreddits askreddit --limit 50 # Monitor askreddit with limit
        """)
    
    parser.add_argument(
        '-s', '--subreddits',
        type=str,
        default='announcements,reddit',
        help='Comma-separated list of subreddits to monitor (default: announcements,reddit)'
    )
    
    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=50,
        help='Maximum number of entries to fetch per subreddit (default: 50)'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='.env',
        help='Path to configuration file (default: .env)'
    )
    
    parser.add_argument(
        '--storage',
        type=str,
        default='banned_users.json',
        help='Path to JSON storage file (default: banned_users.json)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Reddit Ban Tracker 1.0'
    )
    
    return parser


def main():
    """Main entry point with enhanced CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Parse subreddits list
    subreddits = [s.strip() for s in args.subreddits.split(',') if s.strip()]
    
    if not subreddits:
        print("Error: No subreddits specified")
        sys.exit(1)
    
    print(f"Reddit Ban Tracker v1.0")
    print(f"Monitoring subreddits: {', '.join(subreddits)}")
    print(f"Fetch limit: {args.limit}")
    print(f"Config file: {args.config}")
    print(f"Storage file: {args.storage}")
    print("-" * 50)
    
    try:
        # Initialize and run the tracker
        tracker = RedditBanTracker(
            config_file=args.config,
            storage_file=args.storage
        )
        tracker.run(subreddits, limit=args.limit)
        
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()