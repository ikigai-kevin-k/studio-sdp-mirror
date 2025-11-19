"""
Test script for pausing Studio-Roulette-Test table in CIT environment

This script sends a pause_post request to the Studio-Roulette-Test table
in the CIT environment.
"""

import sys
import os

# Add the table_api directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "table_api", "sb"))

from api_v2_cit_sb import pause_post_v2, get_access_token


def main():
    """Main function to test pause_post for Studio-Roulette-Test table"""
    
    # CIT environment configuration
    base_url = "https://crystal-table.iki-cit.cc/v2/service/tables/"
    game_code = "Studio-Roulette-Test"
    post_url = base_url + game_code
    
    # Get access token
    print("=" * 60)
    print("Getting access token for CIT environment...")
    print("=" * 60)
    token = get_access_token(game_code)
    
    if not token:
        print("ERROR: Failed to get access token. Exiting.")
        return 1
    
    print(f"Successfully obtained access token: {token[:20]}...")
    print()
    
    # Reason for pausing
    reason = "Test pause for Studio-Roulette-Test table"
    
    # Send pause_post
    print("=" * 60)
    print(f"Sending pause_post to {game_code}")
    print(f"URL: {post_url}")
    print(f"Reason: {reason}")
    print("=" * 60)
    print()
    
    try:
        pause_post_v2(post_url, token, reason)
        print()
        print("=" * 60)
        print("Pause post completed successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: Failed to send pause_post: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

