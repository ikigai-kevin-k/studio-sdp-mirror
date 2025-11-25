import requests
import sys
import os
import json


def load_env_config():
    """Load environment configuration from table-config-baccarat-v2.json"""
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "conf",
        "table-config-baccarat-v2.json",
    )
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config file: {e}")
        return []


def get_los_env_url(env_name, config):
    """Get LOS environment URL from config by environment name"""
    # Hardcoded environment mappings for environments not in config
    hardcoded_envs = {
        "GLC": "crystal-table.iki-glc.cc",
        "glc": "crystal-table.iki-glc.cc",
        "DEV": "crystal-table.iki-dev.cc",
        "dev": "crystal-table.iki-dev.cc",
    }
    
    # Check hardcoded environments first
    if env_name in hardcoded_envs:
        return hardcoded_envs[env_name]
    
    # Check config file
    for env in config:
        if env.get("name") == env_name:
            # Extract domain from get_url
            url = env.get("get_url", "")
            if url.startswith("https://"):
                # Remove 'https://' prefix and get only the domain part
                domain_part = url[8:]  # Remove 'https://'
                # Split by '/' and take the first part (domain)
                domain = domain_part.split("/")[0]
                return domain
            return url
    return None


def get_access_token(game_code=None, env_name=None):
    """Get a fresh access token from the API

    Args:
        game_code (str): The game code to use (default: BCR-001)
        env_name (str): Environment name from config (CIT, UAT, PRD, STG, QAT, GLC, DEV)
    """
    # Load configuration
    config = load_env_config()

    # Resolve environment URL
    los_env_url = "crystal-table.iki-cit.cc"  # Default fallback
    if env_name and config:
        resolved_url = get_los_env_url(env_name, config)
        if resolved_url:
            los_env_url = resolved_url
            print(f"Resolved {env_name} environment URL: {los_env_url}")

    # Use default values if not provided
    if game_code is None:
        game_code = "BCR-001"

    url = f"https://{los_env_url}/v2/service/sessions"
    headers = {
        "accept": "application/json",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
    }
    data = {"gameCode": game_code, "role": "sdp"}

    try:
        response = requests.post(url, headers=headers, json=data, verify=False)
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get("data", {}).get("token")
        else:
            print(
                f"Error getting token: {response.status_code} - "
                f"{response.text}"
            )
            return None
    except Exception as e:
        print(f"Exception getting token: {e}")
        return None


if __name__ == "__main__":
    # Get arguments from command line or environment variables
    game_code = os.getenv("GAME_CODE") or (
        sys.argv[1] if len(sys.argv) > 1 else None
    )
    env_name = os.getenv("ENV_NAME") or (
        sys.argv[2] if len(sys.argv) > 2 else None
    )

    # Get fresh token
    accessToken = get_access_token(game_code, env_name)
    print("accessToken:", accessToken)
