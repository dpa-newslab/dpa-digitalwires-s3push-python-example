# Import dpa-digitalwires via s3push-API

This example demonstrates how to receive dpa-digitalwires content via the s3push API
using AWS Lambda. The Lambda function processes incoming articles and can optionally
download associated assets (images, videos, etc.) and convert the content to IPTC7901 or
NewsML-G2 format.

## Prerequisites

- Python 3.x
- Node.js and npm
- [serverless Framework V3](https://github.com/serverless/serverless/tree/v3.40.0)
  or [oss-serverless](https://github.com/oss-serverless/serverless)
- [AWS CLI](https://docs.aws.amazon.com/de_de/cli/v1/userguide/cli-chap-configure.html) configured with valid
  credentials

## Quickstart

```shell
cp .env-example .env
nano .env
pip install -r requirements.txt
npm install 
npm run s3push-deploy
```

## Architecture

The setup creates the following AWS resources:

1. **S3 Bucket** - Receives incoming dpa-digitalwires content
2. **SNS Topic** - Notified when new digitalwires-`.json` files arrive in S3
3. **SQS Queue** - Receives messages from SNS. Enables retries and redirection to a dead letter queue after multiple
   failures.
4. **Lambda Function** - Triggered by SQS to process incoming articles

## Environment Variables

Create a `.env` file with the required configuration:

```shell
cp .env-example .env
nano .env
```

### Required Variables

| Variable                 | Description                                                                         |
|--------------------------|-------------------------------------------------------------------------------------|
| `GLOBAL_RESOURCE_PREFIX` | Prefix for all AWS resource names (e.g., `myco`) that will be created on deployment |
| `AWS_REGION`             | AWS region for deployment (e.g., `eu-central-1`)                                    |
| `DEPLOYMENT_BUCKET`      | S3 bucket for Serverless deployment artifacts                                       |

### Optional: Bucket Configuration

Configure the S3 bucket and path prefixes (lowercase only, no leading/trailing slashes):

| Variable         | Default                                                       | Description                                  |
|------------------|---------------------------------------------------------------|----------------------------------------------|
| `S3_BUCKET_NAME` | `${GLOBAL_RESOURCE_PREFIX}-dpa-s3push-incoming-mycompany-com` | The S3 bucket name                           |
| `S3_PREFIX_IN`   | `s3push-receive`                                              | Input path prefix where dpa delivers content |
| `S3_PREFIX_OUT`  | `received`                                                    | Output path prefix for processed files       |

### Optional: Lambda Configuration

Configure the Lambda function behavior:

| Variable              | Default | Description                                                                 |
|-----------------------|---------|-----------------------------------------------------------------------------|
| `DOWNLOAD_ASSETS`     | `true`  | Download associated assets (images, videos, etc.) from the received entries |
| `CONVERT_TO_IPTC`     | `false` | Convert entries to IPTC7901 format and save as `.iptc` files                |
| `CONVERT_TO_NEWSMLG2` | `false` | Convert entries to NewsML-G2 XML format and save as `.xml` files            |

After changing any configuration, redeploy the stack:

```shell
npm run s3push-deploy
```

## Output Structure

Processed files are written to the `S3_PREFIX_OUT` path in S3 with the following structure:

```
{S3_PREFIX_OUT}/
  {original_filename}/
    digitalwire.json              # Original dpa-digitalwires article
    newsmlg2.xml                  # NewsML-G2 (if CONVERT_TO_NEWSMLG2=true)
    {service}.iptc                # IPTC7901 per service (if CONVERT_TO_IPTC=true)
    {urn}-s{size}.{ext}           # Downloaded assets (if DOWNLOAD_ASSETS=true)
    ...
```

The `{original_filename}` is the filename of the incoming JSON file (e.g., `dpa-123456.json`).
Each article is stored in its own folder containing the original JSON, any converted formats,
and downloaded assets.

## Deployment

```shell
pip install -r requirements.txt
npm install
npm run s3push-deploy
```

If the installation was successful, the following output appears:

```shell
Stack Outputs
S3PushDeliveryQueueUrl: https://sqs.eu-central-1.amazonaws.com/{accountId}/{qs_name}]
S3PushSecretAccessKey: xxxx
S3PushUrlPrefix: s3://{s3_bucket_name}/{s3_prefix}
S3PushAccessKeyId: AKIAIxxxxx
...
```

To set up the delivery, please configure the API in the customer portal of dpa-infocom
GmbH (https://api-portal.dpa-newslab.com/api/s3push).

Please enter the output for S3 URL prefix, Access Key ID und Secret Access Key
in the given form.
