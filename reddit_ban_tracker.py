#!/usr/bin/env python3
"""
Reddit Ban Tracker Bot

A bot that fetches the freshest bans from Reddit using PRAW,
tracks previously seen bans in a JSON file, and displays only new bans.

Author: Reddit Ban Tracker Bot
License: MIT
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Set, Optional
import logging
from pathlib import Path

try:
    import praw
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Required dependency not found: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


class RedditBanTracker:
    """A bot to track and display new bans from Reddit."""
    
    def __init__(self, config_file: str = ".env", storage_file: str = "banned_users.json"):
        """
        Initialize the Reddit Ban Tracker.
        
        Args:
            config_file: Path to configuration file with Reddit credentials
            storage_file: Path to JSON file for storing ban history
        """
        self.storage_file = storage_file
        self.logger = self._setup_logging()
        
        # Load environment variables
        load_dotenv(config_file)
        
        # Initialize Reddit connection
        self.reddit = self._initialize_reddit()
        
        # Load existing ban data
        self.previous_bans = self._load_previous_bans()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('reddit_ban_tracker.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def _initialize_reddit(self) -> praw.Reddit:
        """
        Initialize Reddit API connection using PRAW.
        
        Returns:
            Configured PRAW Reddit instance
            
        Raises:
            SystemExit: If credentials are missing or invalid
        """
        try:
            required_vars = [
                'REDDIT_CLIENT_ID',
                'REDDIT_CLIENT_SECRET',
                'REDDIT_USER_AGENT'
            ]
            
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                self.logger.error(f"Missing required environment variables: {missing_vars}")
                self.logger.error("Please set these in your .env file")
                sys.exit(1)
            
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT'),
                # For read-only access, we don't need username/password
            )
            
            # Test the connection
            self.logger.info(f"Connected to Reddit as: {reddit.config.username or 'Read-only'}")
            return reddit
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit connection: {e}")
            sys.exit(1)
    
    def _load_previous_bans(self) -> Dict[str, Dict]:
        """
        Load previously seen bans from JSON storage file.
        
        Returns:
            Dictionary of previously seen banned users
        """
        if not os.path.exists(self.storage_file):
            self.logger.info(f"No existing ban storage file found. Creating new one: {self.storage_file}")
            return {}
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.logger.info(f"Loaded {len(data)} previously seen bans from {self.storage_file}")
                return data
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error reading storage file {self.storage_file}: {e}")
            return {}
    
    def _save_bans(self, bans: Dict[str, Dict]) -> None:
        """
        Save ban data to JSON storage file.
        
        Args:
            bans: Dictionary of ban data to save
        """
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(bans, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"Saved {len(bans)} bans to {self.storage_file}")
        except IOError as e:
            self.logger.error(f"Error saving bans to {self.storage_file}: {e}")
    
    def fetch_banned_users(self, subreddit_names: List[str], limit: int = 100) -> Dict[str, Dict]:
        """
        Fetch banned users from specified subreddits.
        
        Note: This method requires moderator permissions to access ban lists.
        For demonstration purposes, we'll fetch from publicly available data.
        
        Args:
            subreddit_names: List of subreddit names to check
            limit: Maximum number of entries to fetch per subreddit
            
        Returns:
            Dictionary of banned users with ban information
        """
        current_bans = {}
        
        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                self.logger.info(f"Fetching ban data from r/{subreddit_name}")
                
                # Note: banned() requires moderator permissions
                # For public access, we'll need to use alternative methods
                # This is a placeholder for the actual implementation
                
                try:
                    # Attempt to access ban list (requires mod permissions)
                    banned_users = subreddit.banned(limit=limit)
                    
                    for banned_user in banned_users:
                        user_key = f"{subreddit_name}_{banned_user.name}"
                        current_bans[user_key] = {
                            'username': banned_user.name,
                            'subreddit': subreddit_name,
                            'ban_date': getattr(banned_user, 'date', None),
                            'ban_reason': getattr(banned_user, 'note', 'No reason provided'),
                            'moderator': getattr(banned_user, 'mod', 'Unknown'),
                            'fetch_timestamp': datetime.now().isoformat()
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Cannot access ban list for r/{subreddit_name}: {e}")
                    self.logger.info(f"This likely means you don't have moderator permissions for r/{subreddit_name}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                continue
        
        return current_bans
    
    def fetch_public_moderation_data(self, subreddit_names: List[str], limit: int = 100) -> Dict[str, Dict]:
        """
        Fetch publicly available moderation-related data as an alternative to ban lists.
        This includes removed posts, locked threads, etc.
        
        Args:
            subreddit_names: List of subreddit names to check
            limit: Maximum number of entries to fetch per subreddit
            
        Returns:
            Dictionary of moderation actions
        """
        moderation_data = {}
        
        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                self.logger.info(f"Fetching moderation data from r/{subreddit_name}")
                
                # Get moderation log (if available)
                try:
                    mod_log = subreddit.mod.log(limit=limit)
                    
                    for log_entry in mod_log:
                        entry_key = f"{subreddit_name}_{log_entry.id}"
                        moderation_data[entry_key] = {
                            'action': log_entry.action,
                            'moderator': str(log_entry.mod),
                            'target': str(getattr(log_entry, 'target_author', 'N/A')),
                            'subreddit': subreddit_name,
                            'created_utc': log_entry.created_utc,
                            'details': getattr(log_entry, 'details', None),
                            'fetch_timestamp': datetime.now().isoformat()
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Cannot access mod log for r/{subreddit_name}: {e}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching moderation data from r/{subreddit_name}: {e}")
                continue
        
        return moderation_data
    
    def identify_new_bans(self, current_bans: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Compare current bans with previously stored bans to identify new ones.
        
        Args:
            current_bans: Dictionary of current ban data
            
        Returns:
            Dictionary of new bans not seen before
        """
        new_bans = {}
        
        for ban_id, ban_data in current_bans.items():
            if ban_id not in self.previous_bans:
                new_bans[ban_id] = ban_data
        
        self.logger.info(f"Identified {len(new_bans)} new bans out of {len(current_bans)} total")
        return new_bans
    
    def display_new_bans(self, new_bans: Dict[str, Dict]) -> None:
        """
        Display new bans in a formatted manner.
        
        Args:
            new_bans: Dictionary of new ban data to display
        """
        if not new_bans:
            print("\n" + "="*50)
            print("No new bans found!")
            print("="*50)
            return
        
        print("\n" + "="*50)
        print(f"NEW BANS DETECTED: {len(new_bans)}")
        print("="*50)
        
        for ban_id, ban_data in new_bans.items():
            print(f"\nSubreddit: r/{ban_data['subreddit']}")
            print(f"Action: {ban_data.get('action', 'Ban')}")
            
            if 'username' in ban_data:
                print(f"User: u/{ban_data['username']}")
            elif 'target' in ban_data:
                print(f"Target: {ban_data['target']}")
            
            if 'ban_reason' in ban_data:
                print(f"Reason: {ban_data['ban_reason']}")
            elif 'details' in ban_data and ban_data['details']:
                print(f"Details: {ban_data['details']}")
            
            if 'moderator' in ban_data:
                print(f"Moderator: {ban_data['moderator']}")
            
            if 'ban_date' in ban_data and ban_data['ban_date']:
                print(f"Date: {ban_data['ban_date']}")
            elif 'created_utc' in ban_data:
                ban_time = datetime.fromtimestamp(ban_data['created_utc'])
                print(f"Date: {ban_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("-" * 30)
    
    def run(self, subreddit_names: List[str], limit: int = 100) -> None:
        """
        Main execution method to fetch and process ban data.
        
        Args:
            subreddit_names: List of subreddit names to monitor
            limit: Maximum number of entries to fetch per subreddit
        """
        self.logger.info("Starting Reddit Ban Tracker...")
        
        try:
            # First try to fetch actual ban data
            current_bans = self.fetch_banned_users(subreddit_names, limit)
            
            # If no ban data available, try fetching moderation log data
            if not current_bans:
                self.logger.info("No ban data available, trying moderation log data...")
                current_bans = self.fetch_public_moderation_data(subreddit_names, limit)
            
            # Identify new bans
            new_bans = self.identify_new_bans(current_bans)
            
            # Display new bans
            self.display_new_bans(new_bans)
            
            # Update storage with all current bans
            if current_bans:
                self.previous_bans.update(current_bans)
                self._save_bans(self.previous_bans)
            else:
                self.logger.warning("No ban or moderation data was fetched")
            
        except Exception as e:
            self.logger.error(f"Error during execution: {e}")
            raise


def main():
    """Main entry point for the Reddit Ban Tracker."""
    
    # Default subreddits to monitor (can be modified)
    default_subreddits = ['announcements', 'reddit']  # Using public subreddits for testing
    
    # Parse command line arguments (basic implementation)
    subreddits = default_subreddits
    if len(sys.argv) > 1:
        subreddits = sys.argv[1].split(',')
    
    try:
        # Initialize and run the tracker
        tracker = RedditBanTracker()
        tracker.run(subreddits, limit=50)
        
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()