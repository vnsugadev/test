#!/usr/bin/env python3
"""
Mute Banned Users Bot

An optimized bot that automatically responds to and mutes users banned for Rule 7 violations.
This script efficiently processes modmail conversations and handles banned user communications.

Author: Reddit Mute Bot
License: MIT
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import re

try:
    import praw
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Required dependency not found: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


@dataclass
class ProcessedConversation:
    """Data class for tracking processed modmail conversations."""
    conversation_id: str
    user: str
    subreddit: str
    processed_at: str
    action_taken: str
    ban_reason: str


@dataclass
class BotConfig:
    """Configuration data class for the mute bot."""
    target_rule: str = "Rule 7"
    response_template: str = ""
    max_conversations_per_run: int = 50
    conversation_cache_days: int = 30
    dry_run: bool = False
    auto_mute: bool = True
    webhook_url: Optional[str] = None


class ConversationCache:
    """Optimized cache for tracking processed conversations."""
    
    def __init__(self, cache_file: str, retention_days: int = 30):
        self.cache_file = cache_file
        self.retention_days = retention_days
        self._cache: Dict[str, ProcessedConversation] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cached conversations from file."""
        if not os.path.exists(self.cache_file):
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for conv_id, conv_data in data.items():
                self._cache[conv_id] = ProcessedConversation(**conv_data)
                
        except (json.JSONDecodeError, TypeError) as e:
            logging.warning(f"Could not load conversation cache: {e}")
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            cache_data = {
                conv_id: asdict(conv) for conv_id, conv in self._cache.items()
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Could not save conversation cache: {e}")
    
    def _cleanup_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        
        to_remove = []
        for conv_id, conv in self._cache.items():
            try:
                processed_time = datetime.fromisoformat(conv.processed_at)
                if processed_time < cutoff_time:
                    to_remove.append(conv_id)
            except ValueError:
                # Invalid timestamp, remove it
                to_remove.append(conv_id)
        
        for conv_id in to_remove:
            del self._cache[conv_id]
            
        if to_remove:
            logging.info(f"Cleaned up {len(to_remove)} old cache entries")
    
    def is_processed(self, conversation_id: str) -> bool:
        """Check if conversation has been processed."""
        return conversation_id in self._cache
    
    def add_processed(self, conversation: ProcessedConversation) -> None:
        """Add processed conversation to cache."""
        self._cache[conversation.conversation_id] = conversation
        self._cleanup_old_entries()
        self._save_cache()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'total_conversations': len(self._cache),
            'last_24h': sum(1 for conv in self._cache.values() 
                          if self._is_recent(conv.processed_at, hours=24)),
            'last_7d': sum(1 for conv in self._cache.values() 
                         if self._is_recent(conv.processed_at, days=7))
        }
    
    def _is_recent(self, timestamp: str, hours: int = 0, days: int = 0) -> bool:
        """Check if timestamp is within the specified time range."""
        try:
            processed_time = datetime.fromisoformat(timestamp)
            cutoff = datetime.now() - timedelta(hours=hours, days=days)
            return processed_time >= cutoff
        except ValueError:
            return False


class MuteBannedUsersBot:
    """Optimized bot for handling banned user modmail conversations."""
    
    def __init__(self, config_file: str = ".env", 
                 cache_file: str = "processed_conversations.json",
                 config_data: Optional[Dict] = None):
        """
        Initialize the Mute Banned Users Bot.
        
        Args:
            config_file: Path to environment configuration file
            cache_file: Path to processed conversations cache file
            config_data: Optional configuration dictionary override
        """
        self.logger = self._setup_logging()
        
        # Load configuration
        load_dotenv(config_file)
        self.config = self._load_config(config_data or {})
        
        # Initialize Reddit connection
        self.reddit = self._initialize_reddit()
        
        # Initialize conversation cache
        self.conversation_cache = ConversationCache(
            cache_file, 
            self.config.conversation_cache_days
        )
        
        self.logger.info("MuteBannedUsersBot initialized successfully")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('MuteBannedUsersBot')
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler('mute_banned_users.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_config(self, config_override: Dict) -> BotConfig:
        """Load and validate configuration."""
        config_data = {
            'target_rule': os.getenv('TARGET_RULE', 'Rule 7'),
            'response_template': os.getenv('RESPONSE_TEMPLATE', 
                'Your message has been received. Due to your recent ban for {rule}, '
                'your ability to message the moderators has been temporarily restricted.'),
            'max_conversations_per_run': int(os.getenv('MAX_CONVERSATIONS_PER_RUN', 50)),
            'conversation_cache_days': int(os.getenv('CONVERSATION_CACHE_DAYS', 30)),
            'dry_run': os.getenv('DRY_RUN', 'false').lower() == 'true',
            'auto_mute': os.getenv('AUTO_MUTE', 'true').lower() == 'true',
            'webhook_url': os.getenv('WEBHOOK_URL')
        }
        
        # Override with provided config
        config_data.update(config_override)
        
        return BotConfig(**config_data)
    
    def _initialize_reddit(self) -> praw.Reddit:
        """Initialize Reddit API connection with proper error handling."""
        try:
            required_vars = [
                'REDDIT_CLIENT_ID',
                'REDDIT_CLIENT_SECRET',
                'REDDIT_USER_AGENT'
            ]
            
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                self.logger.error(f"Missing required environment variables: {missing_vars}")
                raise ValueError("Required Reddit credentials not found")
            
            # Check if we need authenticated access
            username = os.getenv('REDDIT_USERNAME')
            password = os.getenv('REDDIT_PASSWORD')
            
            if username and password:
                reddit = praw.Reddit(
                    client_id=os.getenv('REDDIT_CLIENT_ID'),
                    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                    user_agent=os.getenv('REDDIT_USER_AGENT'),
                    username=username,
                    password=password
                )
            else:
                self.logger.warning("No Reddit username/password provided, using read-only access")
                reddit = praw.Reddit(
                    client_id=os.getenv('REDDIT_CLIENT_ID'),
                    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                    user_agent=os.getenv('REDDIT_USER_AGENT')
                )
            
            # Test connection
            try:
                user = reddit.user.me()
                self.logger.info(f"Connected to Reddit as: {user.name if user else 'Read-only'}")
            except Exception:
                self.logger.info("Connected to Reddit in read-only mode")
            
            return reddit
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit connection: {e}")
            raise
    
    def _is_rule_violation_ban(self, ban_reason: str) -> bool:
        """Check if ban reason matches target rule."""
        if not ban_reason:
            return False
        
        # Clean and normalize the ban reason
        normalized_reason = ban_reason.lower().strip()
        target_rule_lower = self.config.target_rule.lower()
        
        # Check for exact match or common variations
        patterns = [
            target_rule_lower,
            f"{target_rule_lower} violation",
            f"violating {target_rule_lower}",
            f"broke {target_rule_lower}"
        ]
        
        # Handle "Rule X" specifically - extract number if present
        rule_match = re.match(r'rule\s*(\d+)', target_rule_lower)
        if rule_match:
            rule_num = rule_match.group(1)
            patterns.extend([
                f"rule\\s*{rule_num}",
                f"r{rule_num}",
                rule_num  # Just the number
            ])
        
        return any(re.search(pattern, normalized_reason, re.IGNORECASE) for pattern in patterns)
    
    def get_recent_bans(self, subreddit_name: str, days: int = 7) -> List[Tuple[str, str]]:
        """
        Get recent bans from subreddit for target rule violations.
        
        Args:
            subreddit_name: Name of the subreddit to check
            days: Number of days to look back
            
        Returns:
            List of (username, ban_reason) tuples
        """
        recent_bans = []
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Try to get moderation log for bans
            try:
                mod_actions = subreddit.mod.log(
                    action='banuser',
                    limit=self.config.max_conversations_per_run * 2
                )
                
                for action in mod_actions:
                    try:
                        action_time = datetime.fromtimestamp(action.created_utc)
                        if action_time < cutoff_time:
                            break
                        
                        if (hasattr(action, 'details') and 
                            self._is_rule_violation_ban(action.details)):
                            
                            recent_bans.append((
                                action.target_author,
                                action.details or 'No reason provided'
                            ))
                            
                    except (AttributeError, ValueError) as e:
                        self.logger.debug(f"Skipping invalid mod action: {e}")
                        continue
                        
            except Exception as e:
                self.logger.warning(f"Cannot access mod log for r/{subreddit_name}: {e}")
                
                # Fallback: try to get banned users directly
                try:
                    banned_users = subreddit.banned(limit=100)
                    for banned_user in banned_users:
                        ban_reason = getattr(banned_user, 'note', 'No reason provided')
                        if self._is_rule_violation_ban(ban_reason):
                            recent_bans.append((banned_user.name, ban_reason))
                            
                except Exception as e2:
                    self.logger.warning(f"Cannot access ban list for r/{subreddit_name}: {e2}")
        
        except Exception as e:
            self.logger.error(f"Error getting recent bans for r/{subreddit_name}: {e}")
        
        self.logger.info(f"Found {len(recent_bans)} recent {self.config.target_rule} bans in r/{subreddit_name}")
        return recent_bans
    
    def process_modmail_conversations(self, subreddit_name: str) -> int:
        """
        Process modmail conversations for recently banned users.
        
        Args:
            subreddit_name: Name of the subreddit to process
            
        Returns:
            Number of conversations processed
        """
        processed_count = 0
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get recently banned users for target rule
            recent_bans = self.get_recent_bans(subreddit_name)
            banned_users = {username.lower() for username, _ in recent_bans}
            
            if not banned_users:
                self.logger.info(f"No recent {self.config.target_rule} bans found in r/{subreddit_name}")
                return 0
            
            self.logger.info(f"Processing modmail for {len(banned_users)} recently banned users")
            
            # Get modmail conversations
            try:
                conversations = subreddit.modmail.conversations(
                    state='all', 
                    limit=self.config.max_conversations_per_run
                )
                
                for conversation in conversations:
                    if processed_count >= self.config.max_conversations_per_run:
                        break
                    
                    # Skip if already processed
                    if self.conversation_cache.is_processed(conversation.id):
                        continue
                    
                    # Check if conversation is from a recently banned user
                    if (hasattr(conversation, 'user') and 
                        conversation.user and 
                        conversation.user.name.lower() in banned_users):
                        
                        processed_count += self._handle_banned_user_conversation(
                            conversation, subreddit_name, recent_bans
                        )
                        
                        # Small delay to avoid rate limiting
                        time.sleep(0.5)
                        
            except Exception as e:
                self.logger.error(f"Error accessing modmail for r/{subreddit_name}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error processing r/{subreddit_name}: {e}")
        
        return processed_count
    
    def _handle_banned_user_conversation(self, conversation, subreddit_name: str, 
                                       recent_bans: List[Tuple[str, str]]) -> int:
        """
        Handle a single modmail conversation from a banned user.
        
        Args:
            conversation: PRAW modmail conversation object
            subreddit_name: Name of the subreddit
            recent_bans: List of recent ban information
            
        Returns:
            1 if conversation was processed, 0 otherwise
        """
        try:
            username = conversation.user.name
            
            # Find the ban reason for this user
            ban_reason = next(
                (reason for user, reason in recent_bans if user == username),
                f"{self.config.target_rule} violation"
            )
            
            self.logger.info(f"Processing conversation {conversation.id} from banned user u/{username}")
            
            if not self.config.dry_run:
                # Send response message
                response_message = self.config.response_template.format(
                    rule=self.config.target_rule,
                    username=username,
                    subreddit=subreddit_name
                )
                
                try:
                    conversation.reply(
                        body=response_message,
                        author_hidden=True,
                        internal=False
                    )
                    self.logger.info(f"Sent response to u/{username}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to send response to u/{username}: {e}")
                
                # Mute the conversation if enabled
                if self.config.auto_mute:
                    try:
                        conversation.mute()
                        self.logger.info(f"Muted conversation with u/{username}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to mute conversation with u/{username}: {e}")
            
            else:
                self.logger.info(f"DRY RUN: Would respond and mute conversation with u/{username}")
            
            # Cache the processed conversation
            processed_conv = ProcessedConversation(
                conversation_id=conversation.id,
                user=username,
                subreddit=subreddit_name,
                processed_at=datetime.now().isoformat(),
                action_taken="responded_and_muted" if self.config.auto_mute else "responded_only",
                ban_reason=ban_reason
            )
            
            self.conversation_cache.add_processed(processed_conv)
            
            return 1
            
        except Exception as e:
            self.logger.error(f"Error handling conversation {conversation.id}: {e}")
            return 0
    
    def run(self, subreddit_names: List[str]) -> Dict[str, int]:
        """
        Main execution method to process modmail for banned users.
        
        Args:
            subreddit_names: List of subreddit names to monitor
            
        Returns:
            Dictionary with processing statistics per subreddit
        """
        self.logger.info("Starting MuteBannedUsersBot...")
        
        if self.config.dry_run:
            self.logger.info("Running in DRY RUN mode - no actual actions will be taken")
        
        results = {}
        total_processed = 0
        
        try:
            for subreddit_name in subreddit_names:
                self.logger.info(f"Processing r/{subreddit_name}")
                
                try:
                    processed_count = self.process_modmail_conversations(subreddit_name)
                    results[subreddit_name] = processed_count
                    total_processed += processed_count
                    
                    self.logger.info(f"Processed {processed_count} conversations in r/{subreddit_name}")
                    
                    # Add delay between subreddits
                    if len(subreddit_names) > 1:
                        time.sleep(2)
                        
                except Exception as e:
                    self.logger.error(f"Error processing r/{subreddit_name}: {e}")
                    results[subreddit_name] = 0
            
            # Log summary
            cache_stats = self.conversation_cache.get_stats()
            self.logger.info(f"Session complete: {total_processed} conversations processed")
            self.logger.info(f"Cache stats: {cache_stats}")
            
        except Exception as e:
            self.logger.error(f"Error during execution: {e}")
            raise
        
        return results


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Automatically respond to and mute users banned for Rule 7 violations"
    )
    parser.add_argument(
        '--subreddits', '-s',
        type=str,
        default='announcements,help',
        help='Comma-separated list of subreddit names to monitor'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='.env',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--cache',
        type=str,
        default='processed_conversations.json',
        help='Path to conversation cache file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry mode without taking actual actions'
    )
    parser.add_argument(
        '--rule',
        type=str,
        default='Rule 7',
        help='Target rule for ban detection'
    )
    
    args = parser.parse_args()
    
    # Parse subreddit list
    subreddit_names = [s.strip() for s in args.subreddits.split(',') if s.strip()]
    
    try:
        # Create configuration override
        config_override = {
            'dry_run': args.dry_run,
            'target_rule': args.rule
        }
        
        # Initialize and run bot
        bot = MuteBannedUsersBot(
            config_file=args.config,
            cache_file=args.cache,
            config_data=config_override
        )
        
        results = bot.run(subreddit_names)
        
        print("\nResults:")
        for subreddit, count in results.items():
            print(f"  r/{subreddit}: {count} conversations processed")
        
        total = sum(results.values())
        print(f"\nTotal: {total} conversations processed")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()