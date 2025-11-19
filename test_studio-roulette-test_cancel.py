"""
Test script for canceling STUDIO-ROULETTE-TEST table in CIT environment

This script sends a cancel_post request to the STUDIO-ROULETTE-TEST table
in the CIT environment.
"""

import sys
import os

# Add the table_api directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "table_api", "sb"))

from api_v2_cit_sb import cancel_post, get_access_token


def main():
    """Main function to test cancel_post for STUDIO-ROULETTE-TEST table"""
    
    # CIT environment configuration
    base_url = "https://crystal-table.iki-cit.cc/v2/service/tables/"
    game_code = "STUDIO-ROULETTE-TEST"
    post_url = base_url + game_code
    
    # Get access token
    print("=" * 60)
    print("Getting access token for CIT environment...")
    print("=" * 60)
    token = get_access_token()
    
    if not token:
        print("ERROR: Failed to get access token. Exiting.")
        return 1
    
    print(f"Successfully obtained access token: {token[:20]}...")
    print()
    
    # Send cancel_post
    print("=" * 60)
    print(f"Sending cancel_post to {game_code}")
    print(f"URL: {post_url}")
    print("=" * 60)
    print()
    
    try:
        cancel_post(post_url, token)
        print()
        print("=" * 60)
        print("Cancel post completed successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: Failed to send cancel_post: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

