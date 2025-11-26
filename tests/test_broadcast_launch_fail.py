#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for broadcast_post_v2 function with ROULETTE_LAUNCH_FAIL error type.

This module tests the broadcast_post_v2 function from table_api/sr/api_v2_sr.py
specifically for the ROULETTE_LAUNCH_FAIL error broadcast functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the functions to test
from table_api.sr.api_v2_sr import (
    broadcast_post_v2,
    _get_broadcast_metadata,
)

# Try to import ErrorMsgId, fallback to string if import fails
try:
    from studio_api.ws_err_sig import ErrorMsgId
except ImportError:
    # Fallback: define ErrorMsgId enum locally for testing
    from enum import Enum

    class ErrorMsgId(Enum):
        ROULETTE_LAUNCH_FAIL = "ROULETTE_LAUNCH_FAIL"
        ROULETTE_INVALID_AFTER_RELAUNCH = "ROULETTE_INVALID_AFTER_RELAUNCH"
        ROUELTTE_WRONG_BALL_DIR = "ROUELTTE_WRONG_BALL_DIR"
        ROULETTE_SENSOR_STUCK = "ROULETTE_SENSOR_STUCK"


class TestBroadcastLaunchFail(unittest.TestCase):
    """Test cases for ROULETTE_LAUNCH_FAIL broadcast functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_url = "https://crystal-table.iki-cit.cc/v2/service/tables/ARO-001"
        self.test_token = "E5LN4END9Q"
        self.broadcast_type = "roulette.launch_fail"
        self.expected_msg_id = ErrorMsgId.ROULETTE_LAUNCH_FAIL.value

    def test_get_broadcast_metadata_launch_fail(self):
        """Test _get_broadcast_metadata returns correct data for roulette.launch_fail."""
        result = _get_broadcast_metadata(self.broadcast_type, signal_type="warning")

        # Verify structure
        self.assertIsInstance(result, dict)
        self.assertIn("msgId", result)
        self.assertIn("content", result)
        self.assertIn("metadata", result)

        # Verify msgId
        self.assertEqual(result["msgId"], self.expected_msg_id)

        # Verify content
        self.assertEqual(result["content"], "Roulette launch fail error")

        # Verify metadata structure
        metadata = result["metadata"]
        self.assertIsInstance(metadata, dict)
        self.assertIn("title", metadata)
        self.assertIn("description", metadata)
        self.assertIn("code", metadata)
        self.assertIn("suggestion", metadata)
        self.assertIn("signalType", metadata)

        # Verify metadata values
        self.assertEqual(metadata["title"], "ROULETTE LAUNCH FAIL")
        self.assertEqual(metadata["description"], "Roulette ball launch failed")
        self.assertEqual(metadata["code"], "ARE.2")
        self.assertEqual(metadata["suggestion"], "Check the launch mechanism")
        self.assertEqual(metadata["signalType"], "warning")

    def test_get_broadcast_metadata_launch_fail_error_signal_type(self):
        """Test _get_broadcast_metadata with error signal_type."""
        result = _get_broadcast_metadata(self.broadcast_type, signal_type="error")

        # Verify signalType is error
        self.assertEqual(result["metadata"]["signalType"], "error")
        # Other fields should remain the same
        self.assertEqual(result["msgId"], self.expected_msg_id)
        self.assertEqual(result["metadata"]["title"], "ROULETTE LAUNCH FAIL")

    @patch("table_api.sr.api_v2_sr.requests.post")
    def test_broadcast_post_v2_launch_fail_success(self, mock_post):
        """Test broadcast_post_v2 successfully sends ROULETTE_LAUNCH_FAIL broadcast."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Broadcast sent successfully",
        }
        mock_post.return_value = mock_response

        # Call the function
        broadcast_post_v2(
            self.test_url, self.test_token, self.broadcast_type, "players", 20
        )

        # Verify requests.post was called
        self.assertTrue(mock_post.called)

        # Verify the request was made to the correct URL
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], f"{self.test_url}/broadcast")

        # Verify headers
        headers = call_args[1]["headers"]
        self.assertIn("accept", headers)
        self.assertIn("Bearer", headers)
        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Bearer"], self.test_token)

        # Verify request data structure
        request_data = call_args[1]["json"]
        self.assertIsInstance(request_data, dict)
        self.assertIn("msgId", request_data)
        self.assertIn("content", request_data)
        self.assertIn("metadata", request_data)

        # Verify msgId is ROULETTE_LAUNCH_FAIL
        self.assertEqual(request_data["msgId"], self.expected_msg_id)

        # Verify content
        self.assertEqual(request_data["content"], "Roulette launch fail error")

        # Verify metadata structure and values
        metadata = request_data["metadata"]
        self.assertEqual(metadata["title"], "ROULETTE LAUNCH FAIL")
        self.assertEqual(metadata["description"], "Roulette ball launch failed")
        self.assertEqual(metadata["code"], "ARE.2")
        self.assertEqual(metadata["suggestion"], "Check the launch mechanism")
        self.assertEqual(metadata["signalType"], "warning")

        # Verify verify=False was passed (for SSL)
        self.assertEqual(call_args[1]["verify"], False)

    @patch("table_api.sr.api_v2_sr.requests.post")
    def test_broadcast_post_v2_launch_fail_data_format(self, mock_post):
        """Test that broadcast_post_v2 sends data in the correct format."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        # Call the function
        broadcast_post_v2(
            self.test_url, self.test_token, self.broadcast_type, "players", 20
        )

        # Get the request data
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        # Verify the data structure matches the expected format
        expected_structure = {
            "msgId": str,
            "content": str,
            "metadata": {
                "title": str,
                "description": str,
                "code": str,
                "suggestion": str,
                "signalType": str,
            },
        }

        # Check top-level structure
        self.assertIsInstance(request_data["msgId"], str)
        self.assertIsInstance(request_data["content"], str)
        self.assertIsInstance(request_data["metadata"], dict)

        # Check metadata structure
        metadata = request_data["metadata"]
        self.assertIsInstance(metadata["title"], str)
        self.assertIsInstance(metadata["description"], str)
        self.assertIsInstance(metadata["code"], str)
        self.assertIsInstance(metadata["suggestion"], str)
        self.assertIsInstance(metadata["signalType"], str)

        # Verify no old format fields exist
        self.assertNotIn("locale", metadata)
        self.assertNotIn("timestamp", metadata)

    @patch("table_api.sr.api_v2_sr.requests.post")
    def test_broadcast_post_v2_launch_fail_error_response(self, mock_post):
        """Test broadcast_post_v2 handles error responses gracefully."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "error": "Internal server error",
            "message": "Failed to process broadcast",
        }
        mock_post.return_value = mock_response

        # Call the function - it should not raise an exception
        # (the function doesn't check response status, it just prints)
        try:
            broadcast_post_v2(
                self.test_url, self.test_token, self.broadcast_type, "players", 20
            )
        except Exception as e:
            self.fail(f"broadcast_post_v2 raised an exception: {e}")

        # Verify the request was still made
        self.assertTrue(mock_post.called)

    @patch("table_api.sr.api_v2_sr.requests.post")
    def test_broadcast_post_v2_launch_fail_network_error(self, mock_post):
        """Test broadcast_post_v2 handles network errors gracefully."""
        # Mock network error
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Connection refused"
        )

        # Call the function - it should raise an exception
        with self.assertRaises(requests.exceptions.ConnectionError):
            broadcast_post_v2(
                self.test_url, self.test_token, self.broadcast_type, "players", 20
            )

    def test_broadcast_metadata_launch_fail_vs_other_types(self):
        """Test that launch_fail metadata is different from other broadcast types."""
        launch_fail_metadata = _get_broadcast_metadata("roulette.launch_fail")
        relaunch_metadata = _get_broadcast_metadata("roulette.relaunch")
        wrong_dir_metadata = _get_broadcast_metadata("roulette.wrong_ball_dir")
        sensor_stuck_metadata = _get_broadcast_metadata("roulette.sensor_stuck")

        # Verify msgId is different
        self.assertNotEqual(
            launch_fail_metadata["msgId"], relaunch_metadata["msgId"]
        )
        self.assertNotEqual(
            launch_fail_metadata["msgId"], wrong_dir_metadata["msgId"]
        )
        self.assertNotEqual(
            launch_fail_metadata["msgId"], sensor_stuck_metadata["msgId"]
        )

        # Verify title is different
        self.assertNotEqual(
            launch_fail_metadata["metadata"]["title"],
            relaunch_metadata["metadata"]["title"],
        )
        self.assertNotEqual(
            launch_fail_metadata["metadata"]["title"],
            wrong_dir_metadata["metadata"]["title"],
        )
        self.assertNotEqual(
            launch_fail_metadata["metadata"]["title"],
            sensor_stuck_metadata["metadata"]["title"],
        )

        # Verify code is different
        self.assertNotEqual(
            launch_fail_metadata["metadata"]["code"],
            relaunch_metadata["metadata"]["code"],
        )
        self.assertEqual(
            launch_fail_metadata["metadata"]["code"], "ARE.2"
        )

    def test_broadcast_metadata_launch_fail_error_msg_id(self):
        """Test that launch_fail uses correct ErrorMsgId enum value."""
        result = _get_broadcast_metadata(self.broadcast_type)

        # Verify msgId matches ErrorMsgId enum
        self.assertEqual(result["msgId"], ErrorMsgId.ROULETTE_LAUNCH_FAIL.value)
        self.assertEqual(result["msgId"], "ROULETTE_LAUNCH_FAIL")

    @patch("table_api.sr.api_v2_sr.requests.post")
    def test_broadcast_post_v2_launch_fail_with_custom_audience(self, mock_post):
        """Test broadcast_post_v2 with custom audience parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        # Call with custom audience
        broadcast_post_v2(
            self.test_url,
            self.test_token,
            self.broadcast_type,
            "dealers",
            30,
        )

        # Verify the request was made
        self.assertTrue(mock_post.called)

        # Note: audience and afterSeconds are not in the new format,
        # but function signature still accepts them for backward compatibility
        # The actual data sent uses the new format with metadata only

    def test_broadcast_metadata_launch_fail_default_signal_type(self):
        """Test that default signal_type is 'warning'."""
        result_with_default = _get_broadcast_metadata(self.broadcast_type)
        result_with_warning = _get_broadcast_metadata(
            self.broadcast_type, signal_type="warning"
        )

        # Both should have signalType = "warning"
        self.assertEqual(
            result_with_default["metadata"]["signalType"], "warning"
        )
        self.assertEqual(
            result_with_warning["metadata"]["signalType"], "warning"
        )


class TestBroadcastLaunchFailIntegration(unittest.TestCase):
    """Integration tests for ROULETTE_LAUNCH_FAIL broadcast."""

    @patch("table_api.sr.api_v2_sr.requests.post")
    def test_full_broadcast_flow_launch_fail(self, mock_post):
        """Test the complete flow from broadcast_type to API call."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {"broadcast_id": "test-broadcast-123"},
        }
        mock_post.return_value = mock_response

        test_url = "https://crystal-table.iki-cit.cc/v2/service/tables/ARO-001"
        test_token = "E5LN4END9Q"

        # Execute the broadcast
        broadcast_post_v2(
            test_url, test_token, "roulette.launch_fail", "players", 20
        )

        # Verify the complete request
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        # Verify complete data structure
        self.assertEqual(request_data["msgId"], "ROULETTE_LAUNCH_FAIL")
        self.assertEqual(request_data["content"], "Roulette launch fail error")
        self.assertEqual(
            request_data["metadata"]["title"], "ROULETTE LAUNCH FAIL"
        )
        self.assertEqual(
            request_data["metadata"]["description"], "Roulette ball launch failed"
        )
        self.assertEqual(request_data["metadata"]["code"], "ARE.2")
        self.assertEqual(
            request_data["metadata"]["suggestion"], "Check the launch mechanism"
        )
        self.assertEqual(request_data["metadata"]["signalType"], "warning")


if __name__ == "__main__":
    """
    Run tests from command line.
    
    Usage:
        # From project root directory:
        python3 -m unittest tests.test_broadcast_launch_fail -v
        
        # From tests directory:
        python3 test_broadcast_launch_fail.py
        
        # Direct execution:
        python3 tests/test_broadcast_launch_fail.py
    """
    # Configure test output
    unittest.main(verbosity=2)

