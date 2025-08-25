#!/usr/bin/env python3
"""
Test script for Slack sensor error notification
Tests the send_sensor_error_to_slack function
"""

import sys
import os

# Add current directory to path for imports
sys.path.append(".")
sys.path.append("slack")

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    print("   Install with: pip install python-dotenv")

# Import Slack functions
try:
    from slack_notifier import send_error_to_slack
    print("✅ Successfully imported slack_notifier")
except ImportError as e:
    print(f"❌ Failed to import slack_notifier: {e}")
    print("   Make sure you have installed slack-sdk: pip install slack-sdk")
    sys.exit(1)

def test_sensor_error_notification():
    """Test sending sensor error notification to Slack"""
    print("\n🧪 Testing Slack sensor error notification...")
    
    # Test parameters
    error_message = "SENSOR ERROR - Detected warning_flag=4 in *X;6 message"
    error_code = "SENSOR_STUCK"
    table_name = "ARO-002"
    environment = "VIP_ROULETTE"
    
    print(f"📤 Sending error notification:")
    print(f"   Error: {error_message}")
    print(f"   Code: {error_code}")
    print(f"   Table: {table_name}")
    print(f"   Environment: {environment}")
    
    try:
        # Send the error notification
        success = send_error_to_slack(
            error_message=error_message,
            error_code=error_code,
            table_name=table_name,
            environment=environment
        )
        
        if success:
            print("✅ Error notification sent successfully!")
            return True
        else:
            print("❌ Failed to send error notification")
            return False
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return False

def check_environment_variables():
    """Check if required environment variables are set"""
    print("\n🔍 Checking environment variables...")
    
    required_vars = [
        "SLACK_WEBHOOK_URL",
        "SLACK_BOT_TOKEN", 
        "SLACK_USER_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {masked_value}")
        else:
            print(f"   ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these in your .env file or system environment")
        return False
    else:
        print("   ✅ All required environment variables are set")
        return True

def main():
    """Main test function"""
    print("🚀 Slack Sensor Error Notification Test")
    print("=" * 50)
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    if not env_ok:
        print("\n❌ Environment not properly configured")
        print("   Please check SLACK_SETUP_INSTRUCTIONS.md for setup instructions")
        return
    
    # Test the notification
    success = test_sensor_error_notification()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("   Check your Slack channel for the error notification")
    else:
        print("\n💥 Test failed!")
        print("   Check the error messages above for troubleshooting")

if __name__ == "__main__":
    main()
