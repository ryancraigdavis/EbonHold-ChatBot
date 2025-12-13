# AWS Setup Guide

Complete guide for setting up AWS resources for the EbonHold Discord bot Lambda deployment.

## Prerequisites

- AWS CLI installed and configured
- Doppler CLI installed
- Admin or PowerUser AWS IAM permissions

## Step 1: Create IAM Role for EC2

This role allows the temporary EC2 instance (used for ChromaDB syncing) to access EFS and S3.

```bash
# Create trust policy
cat > ec2-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name EbonHold-EC2-EFS-Role \
  --assume-role-policy-document file://ec2-trust-policy.json

# Attach managed policies
aws iam attach-role-policy \
  --role-name EbonHold-EC2-EFS-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess

aws iam attach-role-policy \
  --role-name EbonHold-EC2-EFS-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create self-terminate policy
cat > ec2-terminate-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:TerminateInstances",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Name": "chromadb-sync"
        }
      }
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name EbonHold-EC2-EFS-Role \
  --policy-name EC2-Self-Terminate \
  --policy-document file://ec2-terminate-policy.json

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name EbonHold-EC2-EFS-Role

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name EbonHold-EC2-EFS-Role \
  --role-name EbonHold-EC2-EFS-Role

echo "✅ IAM role created successfully"
```

## Step 2: Verify Doppler Secrets

Make sure all required secrets are in Doppler:

```bash
doppler secrets --only-names
```

You should see:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `DISCORD_TOKEN`
- `DISCORD_PUBLIC_KEY`
- `GROQ_API_KEY`
- `EFS_FILE_SYSTEM_ID`
- `EFS_ACCESS_POINT_ID`
- `EFS_SECURITY_GROUP_ID`
- `VPC_ID`
- `SUBNET_ID_1`
- `SUBNET_ID_2`

## Step 3: Initial ChromaDB Build

Before deploying, build ChromaDB locally and sync to EFS:

```bash
# Build ChromaDB from guides
doppler run -- uv run python -c "
import asyncio
from pathlib import Path
from src.ebonhold_chatbot.knowledge_base import KnowledgeBase

async def build():
    kb = KnowledgeBase(db_path='./chroma_db')
    await kb.initialize()
    await kb.clear_collection()
    data_dir = Path('src/ebonhold_chatbot/data')
    await kb.load_guides_from_directory(data_dir)
    stats = await kb.get_stats()
    print(f'Built ChromaDB with {stats[\"document_count\"]} documents')

asyncio.run(build())
"

# Create tarball
tar -czf chroma_db.tar.gz -C chroma_db .

# Upload to S3
doppler run -- aws s3 cp chroma_db.tar.gz s3://$(doppler secrets get AWS_S3_BUCKET --plain)/chroma_db.tar.gz

echo "✅ ChromaDB uploaded to S3"
```

## Step 4: Sync ChromaDB to EFS

Run the EC2 sync manually for the first time:

```bash
# Get environment variables
export EFS_FILE_SYSTEM_ID=$(doppler secrets get EFS_FILE_SYSTEM_ID --plain)
export SUBNET_ID=$(doppler secrets get SUBNET_ID_1 --plain)
export SECURITY_GROUP_ID=$(doppler secrets get EFS_SECURITY_GROUP_ID --plain)
export AWS_REGION=$(doppler secrets get AWS_REGION --plain)
export AWS_S3_BUCKET=$(doppler secrets get AWS_S3_BUCKET --plain)

# Create user data script
cat > user-data.sh << 'USERDATA'
#!/bin/bash
set -ex

# Install dependencies
yum install -y amazon-efs-utils aws-cli

# Mount EFS
mkdir -p /mnt/efs
mount -t efs EFS_FILE_SYSTEM_ID:/ /mnt/efs

# Download ChromaDB from S3
aws s3 cp s3://AWS_S3_BUCKET/chroma_db.tar.gz /tmp/chroma_db.tar.gz

# Extract to EFS
mkdir -p /mnt/efs/chroma_db
tar -xzf /tmp/chroma_db.tar.gz -C /mnt/efs/chroma_db
chown -R 1000:1000 /mnt/efs/chroma_db

echo "ChromaDB synced to EFS successfully"

# Self-terminate
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region AWS_REGION
USERDATA

# Substitute variables
sed -i "s/EFS_FILE_SYSTEM_ID/$EFS_FILE_SYSTEM_ID/g" user-data.sh
sed -i "s/AWS_S3_BUCKET/$AWS_S3_BUCKET/g" user-data.sh
sed -i "s/AWS_REGION/$AWS_REGION/g" user-data.sh

# Launch EC2 instance
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 \
  --instance-type t4g.nano \
  --subnet-id $SUBNET_ID \
  --security-group-ids $SECURITY_GROUP_ID \
  --iam-instance-profile Name=EbonHold-EC2-EFS-Role \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=chromadb-sync}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "✅ Launched EC2 instance: $INSTANCE_ID"
echo "Instance will sync ChromaDB and auto-terminate in ~2-3 minutes"
echo "Monitor in EC2 Console or with: aws ec2 describe-instances --instance-ids $INSTANCE_ID"
```

## Step 5: Deploy Lambda

Now deploy the Lambda function:

```bash
# Option A: Deploy via GitHub Actions (recommended)
git add .
git commit -m "Initial Lambda deployment setup"
git push origin main

# GitHub Actions will automatically deploy

# Option B: Deploy manually
cd infrastructure
doppler run --command='bash -c "
sam deploy \
  --template-file template.yaml \
  --stack-name ebonhold-discord-bot \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    EFSFileSystemId=\$EFS_FILE_SYSTEM_ID \
    EFSAccessPointId=\$EFS_ACCESS_POINT_ID \
    VpcId=\$VPC_ID \
    SubnetId1=\$SUBNET_ID_1 \
    SubnetId2=\$SUBNET_ID_2 \
    SecurityGroupId=\$EFS_SECURITY_GROUP_ID \
    DiscordToken=\$DISCORD_TOKEN \
    DiscordPublicKey=\$DISCORD_PUBLIC_KEY \
    GroqApiKey=\$GROQ_API_KEY
"'
```

## Step 6: Configure Discord

1. Get the API Gateway URL from the deployment output
2. Go to [Discord Developer Portal](https://discord.com/developers/applications)
3. Select your application
4. Go to "General Information"
5. Set "Interactions Endpoint URL" to the API Gateway URL
6. Discord will send a test request - if everything is set up correctly, it will verify

## Step 7: Register Slash Commands

```bash
doppler run -- uv run python scripts/register_slash_commands.py
```

## Step 8: Test

In your Discord server, type:

```
/lich what's the best frost DK rotation?
```

The bot should respond!

## Verification Checklist

- [ ] IAM role `EbonHold-EC2-EFS-Role` created
- [ ] All Doppler secrets configured
- [ ] ChromaDB built and synced to EFS
- [ ] Lambda function deployed
- [ ] API Gateway URL configured in Discord
- [ ] Slash commands registered
- [ ] Test command works in Discord

## Troubleshooting

### Lambda times out

- Check CloudWatch logs: `/aws/lambda/ebonhold-discord-bot`
- Verify EFS is mounted: Look for "Cold start" or "Warm start" messages
- Check ChromaDB stats in logs

### Discord says "Application did not respond"

- Lambda must respond within 3 seconds
- Check for cold start issues
- Verify Lambda has internet access (needs NAT Gateway if in private subnet)

### ChromaDB not found

- Verify EFS mount: `ls /mnt/efs/chroma_db` in Lambda
- Check EC2 sync logs in CloudWatch
- Re-run Step 4 to sync again

### Permission errors

- Verify security group allows NFS (port 2049)
- Check EFS access point has correct UID/GID (1000:1000)
- Verify Lambda execution role has VPC and EFS permissions

## Cost Optimization

- Use **One Zone EFS** instead of Standard (saves 50%)
- Enable **EFS Lifecycle Management** to move old files to IA storage
- Use **Lambda reserved concurrency** of 1 (prevents runaway costs)
- Monitor with **AWS Budgets** - set alert at $1/month

## Next Steps

Once everything is working:

1. Set up **CloudWatch Alarms** for Lambda errors
2. Configure **Discord webhook** for deployment notifications
3. Add **monitoring dashboard** in CloudWatch
4. Set up **automated backups** of EFS
5. Consider **CI/CD improvements** (staging environment, etc.)

Congratulations! Your bot is deployed and ready to help Death Knights dominate Mists of Pandaria! 🗡️
