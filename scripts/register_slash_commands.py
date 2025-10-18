#!/usr/bin/env python3
"""
Script to register Discord slash commands for the Lich King bot.
Run this once to set up the /lich command in your Discord application.
"""

import asyncio
import aiohttp
import os
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ebonhold_chatbot.config import Config

async def register_slash_commands():
    """Register the /lich slash command with Discord"""
    try:
        config = Config.from_env()

        # Discord API endpoints
        base_url = "https://discord.com/api/v10"

        # Get application ID from bot token
        async with aiohttp.ClientSession() as session:
            # First, get application info
            headers = {
                "Authorization": f"Bot {config.discord_token}",
                "Content-Type": "application/json"
            }

            async with session.get(f"{base_url}/oauth2/applications/@me", headers=headers) as resp:
                if resp.status != 200:
                    print(f"Failed to get application info: {resp.status}")
                    print(await resp.text())
                    return

                app_data = await resp.json()
                app_id = app_data["id"]
                print(f"Application ID: {app_id}")

            # Define the /lich command
            lich_command = {
                "name": "lich",
                "description": "Ask the Lich King about Death Knight strategies and builds",
                "options": [
                    {
                        "name": "question",
                        "description": "Your Death Knight question for the Lich King",
                        "type": 3,  # STRING type
                        "required": True
                    }
                ]
            }

            # Register command globally (takes up to 1 hour to propagate)
            global_url = f"{base_url}/applications/{app_id}/commands"

            async with session.post(global_url, headers=headers, json=lich_command) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    print("✅ Successfully registered /lich command globally!")
                    print(f"Command ID: {result.get('id')}")
                    print("⏰ Note: Global commands can take up to 1 hour to appear in Discord")
                else:
                    print(f"❌ Failed to register global command: {resp.status}")
                    print(await resp.text())
                    return

            # If guild_id is specified, also register for faster testing
            if config.guild_id:
                guild_url = f"{base_url}/applications/{app_id}/guilds/{config.guild_id}/commands"

                async with session.post(guild_url, headers=headers, json=lich_command) as resp:
                    if resp.status in [200, 201]:
                        result = await resp.json()
                        print("✅ Successfully registered /lich command for test guild!")
                        print(f"Guild Command ID: {result.get('id')}")
                        print("⚡ Guild commands appear immediately")
                    else:
                        print(f"⚠️ Failed to register guild command: {resp.status}")
                        print(await resp.text())

            print("\n🎉 Slash command registration complete!")
            print("\nNext steps:")
            print("1. Deploy your Lambda function")
            print("2. Set up API Gateway")
            print("3. Configure Discord Interactions Endpoint URL")
            print("4. Test with /lich in Discord!")

    except Exception as e:
        print(f"❌ Error registering commands: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🗡️ Registering Lich King slash commands...")
    print("Make sure DISCORD_TOKEN and GROQ_API_KEY are set in your environment")
    print("Optional: Set GUILD_ID for faster testing in a specific server\n")

    asyncio.run(register_slash_commands())