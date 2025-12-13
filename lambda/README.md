# Lambda Deployment

This directory contains the AWS Lambda handler for the EbonHold Discord bot.

## Architecture

- **Lambda Function**: Handles Discord Interactions API (slash commands)
- **EFS Mount**: Provides persistent storage for ChromaDB at `/mnt/efs/chroma_db`
- **VPC**: Lambda runs in VPC to access EFS
- **API Gateway**: Routes Discord interactions to Lambda

## Files

- `handler.py`: Main Lambda entry point

## Dependencies

Dependencies are managed via UV in the main `pyproject.toml`. The deployment script will use:

```bash
uv pip compile pyproject.toml -o lambda/requirements.txt
uv pip install -r lambda/requirements.txt --target ./package
```

This ensures Lambda gets the exact same dependencies as your local environment.

## How It Works

1. Discord sends slash command `/lich <question>` to API Gateway
2. API Gateway triggers Lambda function
3. Lambda verifies Discord signature
4. Lambda loads ChromaDB from EFS mount (or reuses if warm start)
5. Lambda searches knowledge base and generates response
6. Response sent back to Discord

## Cold Start Optimization

The Lambda handler uses global variables to cache initialized services:
- **Cold start**: ~2-3 seconds (initializes ChromaDB from EFS)
- **Warm start**: ~0.5-1 second (reuses cached services)

## Deployment

See `../infrastructure/README.md` for deployment instructions.

## Local Testing

You can test the handler locally (without EFS):

```bash
# Set up test environment
export DISCORD_PUBLIC_KEY="your_key"
export DISCORD_TOKEN="your_token"
export GROQ_API_KEY="your_key"
export EFS_MOUNT_PATH="./chroma_db"

# Activate UV environment
source .venv/bin/activate

# Run test
python -c "
from lambda.handler import lambda_handler
import json

event = {
    'headers': {
        'x-signature-ed25519': 'test',
        'x-signature-timestamp': '123456'
    },
    'body': json.dumps({'type': 1})
}

print(lambda_handler(event, None))
"
```

## Environment Variables

Required in Lambda:
- `DISCORD_PUBLIC_KEY`: Discord app public key
- `DISCORD_TOKEN`: Discord bot token
- `GROQ_API_KEY`: Groq API key
- `EFS_MOUNT_PATH`: Path to EFS mount (default: `/mnt/efs/chroma_db`)
