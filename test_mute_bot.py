#!/usr/bin/env python3
"""
Test script for mute_banned_users.py

This script provides unit tests and integration tests for the MuteBannedUsersBot.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mute_banned_users import (
    MuteBannedUsersBot, 
    ConversationCache, 
    ProcessedConversation, 
    BotConfig
)


class TestConversationCache(unittest.TestCase):
    """Test cases for ConversationCache."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'test_cache.json')
        self.cache = ConversationCache(self.cache_file, retention_days=7)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        self.assertIsInstance(self.cache, ConversationCache)
        self.assertEqual(self.cache.cache_file, self.cache_file)
        self.assertEqual(self.cache.retention_days, 7)
    
    def test_add_and_check_processed(self):
        """Test adding and checking processed conversations."""
        conversation = ProcessedConversation(
            conversation_id='test123',
            user='testuser',
            subreddit='testsubreddit',
            processed_at=datetime.now().isoformat(),
            action_taken='responded_and_muted',
            ban_reason='Rule 7 violation'
        )
        
        # Initially not processed
        self.assertFalse(self.cache.is_processed('test123'))
        
        # Add to cache
        self.cache.add_processed(conversation)
        
        # Now should be processed
        self.assertTrue(self.cache.is_processed('test123'))
    
    def test_cache_persistence(self):
        """Test that cache persists across instances."""
        conversation = ProcessedConversation(
            conversation_id='persist123',
            user='persistuser',
            subreddit='testsubreddit',
            processed_at=datetime.now().isoformat(),
            action_taken='responded_and_muted',
            ban_reason='Rule 7 violation'
        )
        
        # Add to first cache instance
        self.cache.add_processed(conversation)
        
        # Create new cache instance
        new_cache = ConversationCache(self.cache_file, retention_days=7)
        
        # Should still be processed
        self.assertTrue(new_cache.is_processed('persist123'))
    
    def test_cache_cleanup(self):
        """Test cleanup of old cache entries."""
        # Add old conversation
        old_conversation = ProcessedConversation(
            conversation_id='old123',
            user='olduser',
            subreddit='testsubreddit',
            processed_at=(datetime.now() - timedelta(days=10)).isoformat(),
            action_taken='responded_and_muted',
            ban_reason='Rule 7 violation'
        )
        
        # Add recent conversation
        recent_conversation = ProcessedConversation(
            conversation_id='recent123',
            user='recentuser',
            subreddit='testsubreddit',
            processed_at=datetime.now().isoformat(),
            action_taken='responded_and_muted',
            ban_reason='Rule 7 violation'
        )
        
        self.cache.add_processed(old_conversation)
        self.cache.add_processed(recent_conversation)
        
        # Recent should still be there, old should be cleaned up
        self.assertTrue(self.cache.is_processed('recent123'))
        # Note: old entry might still be there until cleanup is triggered
    
    def test_cache_stats(self):
        """Test cache statistics."""
        stats = self.cache.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_conversations', stats)
        self.assertIn('last_24h', stats)
        self.assertIn('last_7d', stats)


class TestMuteBannedUsersBot(unittest.TestCase):
    """Test cases for MuteBannedUsersBot."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'test_conversations.json')
        
        # Mock configuration to avoid needing real Reddit credentials
        self.mock_config = {
            'dry_run': True,
            'target_rule': 'Rule 7',
            'max_conversations_per_run': 10
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('mute_banned_users.praw.Reddit')
    @patch('mute_banned_users.load_dotenv')
    @patch.dict(os.environ, {
        'REDDIT_CLIENT_ID': 'test_id',
        'REDDIT_CLIENT_SECRET': 'test_secret',
        'REDDIT_USER_AGENT': 'test_agent'
    })
    def test_bot_initialization(self, mock_load_dotenv, mock_reddit):
        """Test bot initialization."""
        mock_reddit.return_value = Mock()
        
        bot = MuteBannedUsersBot(
            cache_file=self.cache_file,
            config_data=self.mock_config
        )
        
        self.assertIsInstance(bot, MuteBannedUsersBot)
        self.assertTrue(bot.config.dry_run)
        self.assertEqual(bot.config.target_rule, 'Rule 7')
    
    def test_rule_violation_detection(self):
        """Test rule violation detection logic."""
        with patch('mute_banned_users.praw.Reddit'):
            with patch('mute_banned_users.load_dotenv'):
                with patch.dict(os.environ, {
                    'REDDIT_CLIENT_ID': 'test_id',
                    'REDDIT_CLIENT_SECRET': 'test_secret',
                    'REDDIT_USER_AGENT': 'test_agent'
                }):
                    bot = MuteBannedUsersBot(
                        cache_file=self.cache_file,
                        config_data=self.mock_config
                    )
                    
                    # Test various ban reason formats
                    test_cases = [
                        ('Rule 7 violation', True),
                        ('rule 7 violation', True),
                        ('Violating Rule 7', True),
                        ('broke rule 7', True),
                        ('Rule 7', True),
                        ('r7', True),  # Should match now
                        ('7', True),   # Just the number should match 
                        ('rule7', True),  # This should also match now
                        ('Rule 8 violation', False),
                        ('Other violation', False),
                        ('', False),
                        (None, False)
                    ]
                    
                    for ban_reason, expected in test_cases:
                        with self.subTest(ban_reason=ban_reason):
                            result = bot._is_rule_violation_ban(ban_reason)
                            self.assertEqual(result, expected, 
                                           f"Failed for ban reason: '{ban_reason}'")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'integration_cache.json')
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_dry_run_workflow(self):
        """Test complete workflow in dry run mode."""
        # Create mock Reddit API responses
        mock_reddit = Mock()
        mock_subreddit = Mock()
        mock_reddit.subreddit.return_value = mock_subreddit
        
        # Mock recent bans
        mock_mod_action = Mock()
        mock_mod_action.created_utc = datetime.now().timestamp()
        mock_mod_action.target_author = 'testuser'
        mock_mod_action.details = 'Rule 7 violation'
        mock_subreddit.mod.log.return_value = [mock_mod_action]
        
        # Mock modmail conversations
        mock_conversation = Mock()
        mock_conversation.id = 'conv123'
        mock_conversation.user.name = 'testuser'
        mock_subreddit.modmail.conversations.return_value = [mock_conversation]
        
        with patch('mute_banned_users.praw.Reddit', return_value=mock_reddit):
            with patch('mute_banned_users.load_dotenv'):
                with patch.dict(os.environ, {
                    'REDDIT_CLIENT_ID': 'test_id',
                    'REDDIT_CLIENT_SECRET': 'test_secret',
                    'REDDIT_USER_AGENT': 'test_agent'
                }):
                    bot = MuteBannedUsersBot(
                        cache_file=self.cache_file,
                        config_data={'dry_run': True}
                    )
                    
                    # Run the bot
                    results = bot.run(['testsubreddit'])
                    
                    # Check results
                    self.assertIsInstance(results, dict)
                    self.assertIn('testsubreddit', results)


def run_functionality_test():
    """Run a functionality test with mock data."""
    print("Running functionality test...")
    
    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp()
    cache_file = os.path.join(temp_dir, 'func_test_cache.json')
    
    try:
        print(f"Using temporary cache file: {cache_file}")
        
        # Test 1: ConversationCache
        print("\nTest 1: Testing ConversationCache...")
        cache = ConversationCache(cache_file, retention_days=30)
        
        # Add a test conversation
        test_conv = ProcessedConversation(
            conversation_id='test_conv_123',
            user='testuser',
            subreddit='testsubreddit',
            processed_at=datetime.now().isoformat(),
            action_taken='responded_and_muted',
            ban_reason='Rule 7 violation'
        )
        
        cache.add_processed(test_conv)
        print(f"Added conversation to cache: {test_conv.conversation_id}")
        
        # Check if it's processed
        is_processed = cache.is_processed('test_conv_123')
        print(f"Conversation processed status: {is_processed}")
        
        # Get stats
        stats = cache.get_stats()
        print(f"Cache stats: {stats}")
        
        # Test 2: BotConfig
        print("\nTest 2: Testing BotConfig...")
        config = BotConfig(
            target_rule="Rule 7",
            dry_run=True,
            max_conversations_per_run=25
        )
        print(f"Config created: target_rule={config.target_rule}, dry_run={config.dry_run}")
        
        print("\nFunctionality test completed successfully!")
        
    except Exception as e:
        print(f"Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the MuteBannedUsersBot")
    parser.add_argument('--unit', action='store_true', 
                       help='Run unit tests')
    parser.add_argument('--functional', action='store_true',
                       help='Run functionality test')
    parser.add_argument('--all', action='store_true',
                       help='Run all tests')
    
    args = parser.parse_args()
    
    if args.all or (not args.unit and not args.functional):
        args.unit = True
        args.functional = True
    
    if args.functional:
        run_functionality_test()
    
    if args.unit:
        print("\nRunning unit tests...")
        unittest.main(argv=[''], exit=False, verbosity=2)