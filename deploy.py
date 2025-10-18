#!/usr/bin/env python3
"""
Simple deployment script for the Lich King Discord bot.
Handles the complete deployment process to AWS Lambda.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")

    # Check AWS CLI
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ AWS CLI not configured. Run 'aws configure' first.")
            return False
        print("✅ AWS CLI configured")
    except FileNotFoundError:
        print("❌ AWS CLI not installed. Install it first.")
        return False

    # Check environment variables
    required_vars = ['DISCORD_TOKEN', 'DISCORD_PUBLIC_KEY', 'GROQ_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Set them with doppler or export them directly.")
        return False
    print("✅ Environment variables set")

    return True

def install_dependencies():
    """Install dependencies"""
    print("📦 Installing dependencies...")

    try:
        subprocess.run(['python3', '-m', 'pip', 'install', 'boto3'],
                      check=True, capture_output=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(e.stdout.decode() if e.stdout else "")
        print(e.stderr.decode() if e.stderr else "")
        return False

    return True

def deploy_to_lambda():
    """Deploy to AWS Lambda"""
    print("🚀 Deploying to AWS Lambda...")

    try:
        # Run deployment script
        result = subprocess.run([
            sys.executable,
            'infrastructure/lambda_deployment.py'
        ], check=True, capture_output=True, text=True)

        print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def register_commands():
    """Register Discord slash commands"""
    print("📝 Registering slash commands...")

    try:
        result = subprocess.run([
            sys.executable,
            'scripts/register_slash_commands.py'
        ], check=True, capture_output=True, text=True)

        print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Command registration failed: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def main():
    """Main deployment process"""
    print("🗡️ Lich King Discord Bot - Lambda Deployment")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        print("\n❌ Deployment aborted. Fix the issues above and try again.")
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        print("\n❌ Deployment aborted. Failed to install dependencies.")
        sys.exit(1)

    # Deploy to Lambda
    if not deploy_to_lambda():
        print("\n❌ Deployment failed.")
        sys.exit(1)

    # Register commands
    if not register_commands():
        print("\n⚠️ Deployment succeeded but command registration failed.")
        print("You can register commands manually later.")

    print("\n🎉 Deployment complete!")
    print("\n📋 Next steps:")
    print("1. Go to Discord Developer Portal")
    print("2. Set the Interactions Endpoint URL (shown in deployment output)")
    print("3. Test with /lich in your Discord server")
    print("4. Monitor CloudWatch logs for any issues")

    print(f"\n💰 Expected monthly cost: ~$0.50 for typical usage")
    print(f"📊 Monitor usage in AWS CloudWatch")

if __name__ == "__main__":
    main()