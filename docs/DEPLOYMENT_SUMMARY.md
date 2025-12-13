# EbonHold Discord Bot - Lambda Deployment Summary

## What We Built

You now have a **fully automated, serverless Discord bot deployment** using:
- **AWS Lambda** (serverless compute)
- **AWS EFS** (persistent ChromaDB storage)
- **API Gateway** (Discord webhook endpoint)
- **GitHub Actions** (CI/CD automation)
- **Doppler** (secrets management)

## Project Structure

```
EbonHold-ChatBot/
├── src/ebonhold_chatbot/          # Core bot logic
│   ├── bot.py                      # Gateway bot (local dev)
│   ├── knowledge_base.py           # ChromaDB integration
│   ├── groq_client.py              # Groq LLM client
│   ├── structured_search.py        # WeakAura search
│   └── data/                       # Guide files
│
├── lambda/                         # Lambda-specific code
│   ├── handler.py                  # Lambda entry point
│   └── README.md                   # Lambda docs
│
├── infrastructure/                 # AWS infrastructure as code
│   ├── template.yaml               # SAM CloudFormation template
│   └── README.md                   # Infrastructure docs
│
├── .github/workflows/              # CI/CD automation
│   ├── deploy-lambda.yml           # Deploy Lambda function
│   └── sync-chromadb.yml           # Sync guides to EFS
│
├── docs/                           # Documentation
│   ├── AWS_SETUP.md                # Complete setup guide
│   └── DEPLOYMENT_SUMMARY.md       # This file
│
└── scripts/                        # Helper scripts
    └── register_slash_commands.py  # Register Discord commands
```

## AWS Resources Created

### Already Set Up
✅ **EFS File System**: `fs-0ad27f12c9f28f378`
✅ **EFS Access Point**: `fsap-00a6bb4bb9daa7912`
✅ **VPC**: `vpc-9e1beff8` (default VPC)
✅ **Subnets**: `subnet-ae07f4f4`, `subnet-fc0bac9a`
✅ **Security Group**: `sg-11772862` (allows NFS)
✅ **S3 Bucket**: `ebonhold-discord-bot`

### Need to Create (One-Time)
⏳ **IAM Role**: `EbonHold-EC2-EFS-Role` (for EC2 ChromaDB sync)
⏳ **Lambda Function**: Created by GitHub Actions on first deploy
⏳ **API Gateway**: Created by GitHub Actions on first deploy

## GitHub Actions Workflows

### 1. Deploy Lambda (`deploy-lambda.yml`)

**Triggers:**
- Push to `main` branch when code changes in `src/`, `lambda/`, or `infrastructure/`
- Manual workflow dispatch

**What it does:**
1. ✅ Checks out code
2. ✅ Installs UV and Python 3.12
3. ✅ Gets AWS credentials from Doppler
4. ✅ Builds Lambda package with dependencies
5. ✅ Deploys using AWS SAM
6. ✅ Gets API Gateway URL
7. ✅ Registers Discord slash commands

**Result:** Lambda function deployed and ready to handle Discord commands

### 2. Sync ChromaDB (`sync-chromadb.yml`)

**Triggers:**
- Push to `main` when files in `src/ebonhold_chatbot/data/` change
- Manual workflow dispatch

**What it does:**
1. ✅ Builds ChromaDB from guide files
2. ✅ Creates tarball and uploads to S3
3. ✅ Launches temporary t4g.nano EC2 instance
4. ✅ EC2 mounts EFS, downloads from S3, extracts to EFS
5. ✅ EC2 auto-terminates after sync

**Result:** ChromaDB updated on EFS with latest guide content

## Deployment Flow

```
Developer pushes code to GitHub
         │
         ▼
   GitHub Actions triggered
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 Code      Guides
Changed   Changed
    │         │
    ▼         ▼
Deploy    Sync
Lambda    ChromaDB
    │         │
    └────┬────┘
         │
         ▼
   Bot Updated! 🎉
```

## Cost Breakdown

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Lambda | $0 - $0.50 | Free tier covers ~1M requests |
| EFS (One Zone) | $0.02 | ~100MB @ $0.16/GB |
| API Gateway | $0 | Free tier covers 1M requests |
| EC2 (sync) | $0.003 | t4g.nano, ~5 min/month |
| S3 | $0.002 | ~100MB storage |
| **Total** | **~$0.03/month** | After free tier: ~$0.50/month |

**Comparison:**
- Traditional server (EC2 t3.micro): ~$10/month
- Fargate: ~$5-15/month
- This solution: **~$0.50/month** ⚡

## Next Steps to Complete Deployment

Follow the guide at `docs/AWS_SETUP.md`:

1. **Create IAM Role** for EC2 (Step 1)
2. **Build and sync ChromaDB** to EFS (Steps 3-4)
3. **Push to GitHub** - triggers automatic Lambda deployment
4. **Configure Discord** with API Gateway URL (Step 6)
5. **Test** the `/lich` command (Step 8)

## Development Workflow

### Local Development (Gateway Bot)

```bash
# Run locally with Discord Gateway API
source .venv/bin/activate
doppler run -- uv run -m ebonhold_chatbot
```

Use mentions and DMs to test.

### Adding New Guides

1. Add `.txt` or `.md` files to `src/ebonhold_chatbot/data/`
2. Commit and push to `main`
3. GitHub Actions automatically syncs to EFS
4. Lambda picks up changes on next cold start

### Updating Code

1. Modify code in `src/` or `lambda/`
2. Commit and push to `main`
3. GitHub Actions automatically deploys Lambda
4. Changes live immediately

## Monitoring

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/ebonhold-discord-bot --follow

# View EC2 sync logs
aws logs tail /aws/ec2/chromadb-sync --follow
```

### Metrics

Monitor in CloudWatch Console:
- Lambda invocations
- Lambda duration (should be <3s)
- Lambda errors
- EFS throughput

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Lambda timeout | Check EFS mount, verify ChromaDB exists |
| Discord "no response" | Check CloudWatch logs, verify 3s response time |
| ChromaDB empty | Run sync workflow manually |
| Slash command not found | Re-run `register_slash_commands.py` |
| Permission denied | Check security group, EFS access point |

## Key Features

✅ **Serverless** - No servers to maintain
✅ **Auto-scaling** - Handles 1 or 1000 requests
✅ **Cost-effective** - ~$0.50/month
✅ **Automated** - Push to deploy
✅ **Persistent** - ChromaDB survives restarts
✅ **Fast** - <2s response time (warm starts)
✅ **Secure** - Secrets via Doppler
✅ **Version controlled** - Infrastructure as code

## Support

- **Infrastructure docs**: `infrastructure/README.md`
- **Setup guide**: `docs/AWS_SETUP.md`
- **Lambda docs**: `lambda/README.md`
- **GitHub Issues**: For bugs and features

---

**You're all set!** Follow `docs/AWS_SETUP.md` to complete the one-time setup, then push to GitHub to deploy. The bot will automatically stay up-to-date with your code and guide changes. 🗡️
