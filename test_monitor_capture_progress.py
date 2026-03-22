#!/usr/bin/env python3
"""
Unit Tests for Monitor Capture Progress Skill

Tests core logic functions without requiring database access.
Uses pytest framework for structured testing.

Usage:
    # Run all tests
    pytest test_monitor_capture_progress.py -v

    # Run specific test
    pytest test_monitor_capture_progress.py::test_is_capture_complete -v

    # Run with coverage
    pytest test_monitor_capture_progress.py --cov=monitor-capture-progress

Requirements:
    pip install pytest pytest-mock

Author: Claude Sonnet 4.5
Created: 2025-12-27
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from io import StringIO

# Import functions from monitor-capture-progress.py
# Note: Using importlib since the file has hyphens in its name
import importlib.util
spec = importlib.util.spec_from_file_location(
    "monitor_capture_progress",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor-capture-progress.py")
)
monitor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor_module)

# Extract functions
is_capture_complete = monitor_module.is_capture_complete
get_latest_capture = monitor_module.get_latest_capture
get_quality_score = monitor_module.get_quality_score
display_progress = monitor_module.display_progress
display_completion = monitor_module.display_completion


class TestIsCaptureComplete:
    """Test the is_capture_complete() function."""

    def test_complete_with_valid_summary(self):
        """Test capture is complete when summary > 100 chars."""
        snapshot = {
            'id': 1,
            'summary_len': 250,
            'has_embedding': 1
        }
        assert is_capture_complete(snapshot) is True

    def test_incomplete_with_short_summary(self):
        """Test capture is incomplete when summary <= 100 chars."""
        snapshot = {
            'id': 1,
            'summary_len': 50,
            'has_embedding': 0
        }
        assert is_capture_complete(snapshot) is False

    def test_incomplete_with_no_summary(self):
        """Test capture is incomplete when summary is 0."""
        snapshot = {
            'id': 1,
            'summary_len': 0,
            'has_embedding': 0
        }
        assert is_capture_complete(snapshot) is False

    def test_incomplete_with_none_summary(self):
        """Test capture is incomplete when summary is None."""
        snapshot = {
            'id': 1,
            'summary_len': None,
            'has_embedding': 0
        }
        assert is_capture_complete(snapshot) is False

    def test_complete_at_boundary(self):
        """Test capture is complete at exactly 101 chars."""
        snapshot = {
            'id': 1,
            'summary_len': 101,
            'has_embedding': 0
        }
        assert is_capture_complete(snapshot) is True

    def test_none_snapshot(self):
        """Test None snapshot returns False."""
        assert is_capture_complete(None) is False


class TestGetLatestCapture:
    """Test the get_latest_capture() function."""

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_latest_without_session_id(self, mock_db):
        """Test getting latest capture without session ID."""
        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            34,                          # id
            'auto-capture-12cd285c',     # trigger_event
            '2025-12-27 20:15:00',       # timestamp
            480,                          # message_count
            2849,                         # summary_len
            1,                            # has_embedding
            8,                            # tag_count
            23                            # file_count
        )

        result = get_latest_capture(mock_cursor)

        # Verify query was called
        mock_cursor.execute.assert_called_once()
        query = mock_cursor.execute.call_args[0][0]
        assert 'auto-capture%' in query

        # Verify result
        assert result['id'] == 34
        assert result['summary_len'] == 2849
        assert result['message_count'] == 480

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_latest_with_session_id(self, mock_db):
        """Test getting latest capture with specific session ID."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            34, 'auto-capture-abc123', '2025-12-27 20:15:00',
            100, 500, 1, 5, 10
        )

        result = get_latest_capture(mock_cursor, session_id='abc123')

        # Verify query includes session ID
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert 'auto-capture-abc123%' in args[1]

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_latest_no_results(self, mock_db):
        """Test when no captures found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        result = get_latest_capture(mock_cursor)

        assert result is None

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_latest_with_null_values(self, mock_db):
        """Test handling of NULL values in database."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            1, 'auto-capture-test', '2025-12-27',
            None, 0, 0, 0, 0  # NULL values
        )

        result = get_latest_capture(mock_cursor)

        assert result is not None
        assert result['id'] == 1
        assert result['message_count'] is None
        assert result['summary_len'] == 0


class TestGetQualityScore:
    """Test the get_quality_score() function."""

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_quality_score_success(self, mock_db):
        """Test successful quality score retrieval."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (8.523,)

        score = get_quality_score(mock_cursor, 34)

        assert score == 8.5  # Rounded to 1 decimal

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_quality_score_not_found(self, mock_db):
        """Test when snapshot not found in view."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        score = get_quality_score(mock_cursor, 999)

        assert score is None

    @patch('monitor_capture_progress.get_db_connection')
    def test_get_quality_score_view_error(self, mock_db):
        """Test graceful degradation when view doesn't exist."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("relation does not exist")

        score = get_quality_score(mock_cursor, 34)

        assert score is None  # Gracefully returns None


class TestDisplayProgress:
    """Test the display_progress() function."""

    def test_display_progress_processing_summary(self, capsys):
        """Test progress display when processing summary."""
        snapshot = {
            'id': 34,
            'summary_len': 0,
            'has_embedding': 0
        }

        display_progress(snapshot, 15)

        captured = capsys.readouterr()
        assert "🔄 Processing summary..." in captured.out
        assert "(15s elapsed)" in captured.out
        assert "Snapshot ID: 34" in captured.out

    def test_display_progress_generating_embeddings(self, capsys):
        """Test progress display when generating embeddings."""
        snapshot = {
            'id': 34,
            'summary_len': 500,
            'has_embedding': 0
        }

        display_progress(snapshot, 38)

        captured = capsys.readouterr()
        assert "🔄 Generating embeddings..." in captured.out
        assert "(38s elapsed)" in captured.out

    def test_display_progress_finalizing(self, capsys):
        """Test progress display when finalizing."""
        snapshot = {
            'id': 34,
            'summary_len': 500,
            'has_embedding': 1
        }

        display_progress(snapshot, 60)

        captured = capsys.readouterr()
        assert "🔄 Finalizing..." in captured.out


class TestDisplayCompletion:
    """Test the display_completion() function."""

    def test_display_completion_full_details(self, capsys):
        """Test completion display with all details."""
        snapshot = {
            'id': 34,
            'timestamp': '2025-12-27 20:16:05',
            'message_count': 480,
            'summary_len': 1435,  # ~287 words
            'tag_count': 8,
            'file_count': 23
        }

        display_completion(snapshot, 67, quality_score=8.5)

        captured = capsys.readouterr()
        assert "✅ Capture complete! (67s total)" in captured.out
        assert "Snapshot Details:" in captured.out
        assert "ID: 34" in captured.out
        assert "Messages: 480" in captured.out
        assert "287 words" in captured.out
        assert "Tags: 8" in captured.out
        assert "Files: 23" in captured.out
        assert "Quality Score: 8.5/10" in captured.out
        assert "Safe to close Claude Code!" in captured.out
        assert "/mem-enhance-summary 34" in captured.out

    def test_display_completion_minimal_details(self, capsys):
        """Test completion display with minimal details."""
        snapshot = {
            'id': 1,
            'timestamp': '2025-12-27 20:00:00',
            'message_count': None,
            'summary_len': 150,
            'tag_count': 0,
            'file_count': 0
        }

        display_completion(snapshot, 30)

        captured = capsys.readouterr()
        assert "ID: 1" in captured.out
        assert "Messages:" not in captured.out  # None, so skipped
        assert "30 words" in captured.out  # 150 / 5
        assert "Tags:" not in captured.out  # 0, so skipped
        assert "Files:" not in captured.out  # 0, so skipped


class TestIntegrationScenarios:
    """Integration-style tests for common scenarios."""

    @patch('monitor_capture_progress.get_db_connection')
    def test_typical_capture_lifecycle(self, mock_db):
        """Test typical capture lifecycle: processing → complete."""
        mock_cursor = MagicMock()

        # First poll: processing
        mock_cursor.fetchone.return_value = (
            34, 'auto-capture-test', '2025-12-27',
            100, 0, 0, 0, 0  # No summary yet
        )
        snapshot1 = get_latest_capture(mock_cursor)
        assert is_capture_complete(snapshot1) is False

        # Second poll: summary generated
        mock_cursor.fetchone.return_value = (
            34, 'auto-capture-test', '2025-12-27',
            100, 500, 0, 5, 10  # Summary complete
        )
        snapshot2 = get_latest_capture(mock_cursor)
        assert is_capture_complete(snapshot2) is True

    def test_edge_case_boundary_summary_length(self):
        """Test edge cases around 100-character boundary."""
        # Exactly 100: incomplete
        snapshot_100 = {'id': 1, 'summary_len': 100, 'has_embedding': 0}
        assert is_capture_complete(snapshot_100) is False

        # 101: complete
        snapshot_101 = {'id': 1, 'summary_len': 101, 'has_embedding': 0}
        assert is_capture_complete(snapshot_101) is True

        # 99: incomplete
        snapshot_99 = {'id': 1, 'summary_len': 99, 'has_embedding': 0}
        assert is_capture_complete(snapshot_99) is False


# Pytest configuration
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
