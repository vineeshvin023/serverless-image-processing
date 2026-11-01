# Serverless Image Processing Pipeline

## Project Overview

This project creates image thumbnails using AWS serverless services. Images are stored in a source S3 bucket, resized by a Python Lambda function, and saved in a destination bucket.

The function preserves the image’s proportions and produces a JPEG thumbnail within 200 × 200 pixels.

## Architecture

The application supports two processing paths:

- **Automatic processing:** Upload image → S3 event → Lambda → destination S3 bucket.
- **API processing:** POST request → API Gateway → Step Functions → Lambda → destination S3 bucket.

The workflow checks the Lambda result and routes execution to the appropriate success or failure state.

## AWS Services Used

- **Amazon S3:** Stores original images and generated thumbnails.
- **AWS Lambda:** Runs the image resizing code.
- **AWS Step Functions:** Coordinates the processing workflow.
- **Amazon API Gateway:** Provides a REST API to start the workflow.
- **AWS IAM:** Grants permissions between services.
- **Amazon CloudWatch:** Stores logs for troubleshooting.

## Prerequisites

- An AWS account with permission to create the required resources.
- A GitHub repository.
- Python and pip installed locally to build the Pillow layer.
- A valid JPG or PNG image for testing.

Use the same AWS Region for the application’s resources. This project uses `us-east-1`.

Repository files:

```text
lambda_function.py
state_machine.json
requirements.txt
.gitignore
README.md
```

## Create the S3 Buckets

Create two buckets with globally unique names:

- Source: `vineesh-original-images-ccmp200-cap`
- Destination: `vineesh-thumbnail-images-ccmp200-cap`

Keep public access blocked. Upload a valid image named `sample.jpg` to the source bucket.

## Configure Lambda Permissions

Create a Lambda execution role with:

- The `AWSLambdaBasicExecutionRole` managed policy for CloudWatch logging.
- `s3:GetObject` permission on objects in the source bucket.
- `s3:PutObject` permission on objects in the destination bucket.

Use these object resource patterns, replacing bucket names if necessary:

```text
arn:aws:s3:::vineesh-original-images-ccmp200-cap/*
arn:aws:s3:::vineesh-thumbnail-images-ccmp200-cap/*
```

Assign each permission to its corresponding bucket.

## Build and Attach the Pillow Layer

This project uses **Python 3.14**, **x86_64**, and **Pillow 12.2.0**.

From a local project folder, install the Linux-compatible package:

```powershell
python -m pip install --platform manylinux2014_x86_64 --implementation cp --python-version 3.14 --only-binary=:all: --target pillow-layer-py314/python Pillow==12.2.0
```

Create the layer archive:

```powershell
Compress-Archive -Path pillow-layer-py314/python -DestinationPath pillow-layer-python314-x86_64.zip
```

The archive must contain a top-level `python/` folder.

In Lambda, create a layer or publish a new layer version using this ZIP. Select Python 3.14 and x86_64, then attach that version to the function.

The layer’s compatible-runtime setting does not convert its binaries. The packaged Pillow library must match the function’s Python version and architecture.

## Deploy the Lambda Function

Create a Lambda function with:

- Runtime: **Python 3.14**
- Architecture: **x86_64**
- Handler: `lambda_function.lambda_handler`
- Execution role: The Lambda role configured above

Paste the contents of `lambda_function.py` into the code editor and deploy.

Set these environment variables:

```text
SOURCE_BUCKET=vineesh-original-images-ccmp200-cap
DESTINATION_BUCKET=vineesh-thumbnail-images-ccmp200-cap
```

Attach the Python 3.14 Pillow layer.

The function accepts either an S3 event or a direct JSON input containing `bucket` and `key`.

## Configure the S3 Trigger

In the Lambda function, choose **Add trigger → S3**.

Select the source bucket and an object-created event. Confirm the trigger configuration allows S3 to invoke the function.

Use the source bucket for the trigger so generated thumbnails in the destination bucket do not trigger further processing.

Upload a valid image and check the destination bucket for its thumbnail.

## Create the Step Functions Workflow

Create a state machine named `MyStateMachine-ImageResize` using the definition in `state_machine.json`.

Configure the Lambda task to invoke the image-processing function. Give the state machine’s execution role `lambda:InvokeFunction` permission on that function.

The successful processing route is:

```text
ResizeImage → CheckResult → ProcessingSucceeded
```

Ensure `CheckResult` checks the Lambda result’s `success` value and sends unsuccessful results to the failure route.

## Configure API Gateway

Create a Regional REST API named `ImageProcessingAPI`.

Create the `/vinuResize` resource and a POST method with:

- Integration type: **AWS service**
- Service: **Step Functions**
- Region: **us-east-1**
- Integration HTTP method: **POST**
- Action: **StartExecution**
- Execution role: **APIGatewayStartImageWorkflow**

The API Gateway role must trust `apigateway.amazonaws.com` and allow `states:StartExecution` on the state machine.

Add an `application/json` request mapping template:

```text
{
  "input": "$util.escapeJavaScript($input.body).replaceAll("\\'","'")",
  "stateMachineArn": "YOUR-STATE-MACHINE-ARN"
}
```

Replace the placeholder with the state machine ARN copied from Step Functions. Use the state machine ARN, rather than an IAM role ARN.

Save the method configuration. To make the endpoint available outside the console test, deploy the API to a stage and copy its invoke URL.

## Test the Application

Use this input for a direct Lambda test, a Step Functions execution, or the API Gateway POST method test:

```json
{
  "bucket": "vineesh-original-images-ccmp200-cap",
  "key": "sample.jpg"
}
```

Confirm the source object exists and contains a valid image.

Expected results:

1. Lambda returns `"success": true`.
2. Step Functions finishes with status **Succeeded**.
3. The destination bucket contains `thumbnails/sample.jpg.jpg`.

The repeated `.jpg` extension follows the current function’s naming rule: `thumbnails/{original-key}.jpg`.

A successful API request returns `executionArn` and `startDate`. This confirms the workflow started. Check the execution in Step Functions to confirm processing completed.

Download the generated thumbnail and verify it opens. Processing the same source key again overwrites the same destination object.

## Troubleshooting

### Pillow `_imaging` import error

Rebuild the layer for Python 3.14 and x86_64 Linux. Attach the correct layer version to the function.

### `UnidentifiedImageError`

The downloaded object is not recognized as an image. Verify the test event points to the correct object and that the downloaded file opens as a JPG or PNG. Renaming a non-image file does not convert it.

### `InvalidArn` from Step Functions

Check the mapping template’s `stateMachineArn`. It must contain the state machine ARN, beginning with `arn:aws:states:`.

### `AccessDeniedException` for `states:StartExecution`

Grant the `APIGatewayStartImageWorkflow` role permission to start the specific state machine.

### S3 access errors

Check the Lambda role’s S3 permissions, environment variables, bucket name, and exact object key.

### Green Lambda banner with `"success": false`

The handler caught a processing exception. Open the CloudWatch logs and inspect the error traceback.

### API status 200 with an error response

Inspect the response body and integration logs. The current API response mapping can return HTTP 200 even when Step Functions rejects the request.

## Cleanup

After completing the project:

1. Delete the API Gateway API.
2. Stop any running workflow executions and delete the state machine.
3. Remove the S3 trigger and delete the Lambda function.
4. Delete unused Pillow layer versions.
5. Empty and delete both S3 buckets.
6. Delete project-specific CloudWatch log groups.
7. Delete project-specific IAM roles and policies after confirming they are no longer used.

Remove only resources created for this project.
