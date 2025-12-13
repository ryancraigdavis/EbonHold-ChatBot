# Infrastructure Setup

This directory contains AWS infrastructure as code for deploying the EbonHold Discord bot to Lambda with EFS storage.

## Architecture

```
┌─────────────┐
│   Discord   │
└──────┬──────┘
       │ HTTPS POST
       ▼
┌─────────────────┐
│  API Gateway    │
│  /interactions  │
└────────┬────────┘
         │
         ▼
┌────────────────────┐       ┌──────────────┐
│  Lambda Function   │◄──────┤     EFS      │
│  ebonhold-bot      │       │  ChromaDB    │
│                    │       │  Storage     │
│  - VPC attached    │       └──────────────┘
│  - EFS mounted at  │
│    /mnt/efs        │
└────────────────────┘
```

## Files

- `template.yaml`: SAM CloudFormation template defining Lambda, API Gateway, and EFS mount configuration
- `README.md`: This file

## One-Time AWS Setup

Before deploying, you need to create these AWS resources manually (already done if you followed the initial setup):

1. **EFS File System** (`fs-0ad27f12c9f28f378`)
2. **EFS Access Point** (`fsap-00a6bb4bb9daa7912`)
3. **VPC and Subnets** (using default VPC)
4. **Security Group** (`sg-11772862`) with NFS inbound rule
5. **IAM Role for EC2** (EbonHold-EC2-EFS-Role) - see below

### Creating the EC2 IAM Role

The ChromaDB sync workflow needs an IAM role for the temporary EC2 instance. Create it:

```bash
# Create the trust policy
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

# Attach policies
aws iam attach-role-policy \
  --role-name EbonHold-EC2-EFS-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess

aws iam attach-role-policy \
  --role-name EbonHold-EC2-EFS-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Allow EC2 to terminate itself
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

echo "✅ IAM role created: EbonHold-EC2-EFS-Role"
```

## Deployment

Deployment is fully automated via GitHub Actions:

### Automatic Deployment

1. **Lambda deployment** - Triggers on push to `main` when code changes:
   - Builds Lambda package with UV
   - Deploys using SAM
   - Registers Discord slash commands

2. **ChromaDB sync** - Triggers on push to `main` when guide files change:
   - Builds ChromaDB from guides locally
   - Uploads to S3
   - Spins up temporary EC2 instance
   - Syncs to EFS
   - Auto-terminates EC2 instance

### Manual Deployment

You can also deploy manually from your local machine:

```bash
# 1. Load secrets from Doppler
doppler run --command='bash'

# 2. Build Lambda package
mkdir -p package
uv pip install --python 3.12 --target package chromadb groq PyNaCl attrs pyyaml aiofiles
cp -r src/ebonhold_chatbot package/
cp lambda/handler.py package/

# 3. Deploy with SAM
cd infrastructure
sam deploy \
  --template-file template.yaml \
  --stack-name ebonhold-discord-bot \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    EFSFileSystemId=$EFS_FILE_SYSTEM_ID \
    EFSAccessPointId=$EFS_ACCESS_POINT_ID \
    VpcId=$VPC_ID \
    SubnetId1=$SUBNET_ID_1 \
    SubnetId2=$SUBNET_ID_2 \
    SecurityGroupId=$EFS_SECURITY_GROUP_ID \
    DiscordToken=$DISCORD_TOKEN \
    DiscordPublicKey=$DISCORD_PUBLIC_KEY \
    GroqApiKey=$GROQ_API_KEY

# 4. Get API Gateway URL
sam list stack-outputs --stack-name ebonhold-discord-bot
```

## Monitoring

### CloudWatch Logs

Lambda logs are automatically sent to CloudWatch:

```bash
# View logs
aws logs tail /aws/lambda/ebonhold-discord-bot --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/ebonhold-discord-bot \
  --filter-pattern "ERROR"
```

### Metrics

Monitor Lambda performance in CloudWatch:
- Invocations
- Duration
- Errors
- Concurrent executions

## Cost Breakdown

Estimated monthly costs (assuming 1000 commands/month):

| Service | Usage | Cost |
|---------|-------|------|
| Lambda (512MB, 2s avg) | 1000 invocations | $0.00 (free tier) |
| API Gateway | 1000 requests | $0.00 (free tier) |
| EFS (One Zone) | ~100MB storage | $0.016 |
| EC2 (t4g.nano, 5 min/month) | Sync operations | $0.0003 |
| S3 | ~100MB storage | $0.002 |
| **Total** | | **~$0.02/month** |

After free tier expires: ~$0.50/month

## Troubleshooting

### Lambda can't access EFS

1. Check security group allows NFS (port 2049)
2. Verify Lambda is in same VPC/subnets as EFS mount targets
3. Check EFS access point permissions (1000:1000)

### ChromaDB not found

1. Run the ChromaDB sync workflow manually
2. Check EC2 instance CloudWatch logs
3. Verify files exist on EFS: connect to Lambda and `ls /mnt/efs/chroma_db`

### Deployment fails

1. Check SAM has necessary IAM permissions
2. Verify all Doppler secrets are set
3. Check CloudFormation stack events for specific errors

## Cleanup

To delete all resources:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name ebonhold-discord-bot

# Delete EFS (if desired)
aws efs delete-file-system --file-system-id fs-0ad27f12c9f28f378

# Delete IAM role
aws iam remove-role-from-instance-profile \
  --instance-profile-name EbonHold-EC2-EFS-Role \
  --role-name EbonHold-EC2-EFS-Role
aws iam delete-instance-profile --instance-profile-name EbonHold-EC2-EFS-Role
aws iam delete-role-policy --role-name EbonHold-EC2-EFS-Role --policy-name EC2-Self-Terminate
aws iam detach-role-policy --role-name EbonHold-EC2-EFS-Role --policy-arn arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess
aws iam detach-role-policy --role-name EbonHold-EC2-EFS-Role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name EbonHold-EC2-EFS-Role
```
