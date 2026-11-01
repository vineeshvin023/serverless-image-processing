import io
import logging
import os
from urllib.parse import unquote_plus

import boto3
from PIL import Image, ImageOps

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]


def resize_image(bucket, key):
    if bucket != SOURCE_BUCKET:
        raise ValueError("Unexpected source bucket")

    response = s3.get_object(Bucket=bucket, Key=key)

    with Image.open(io.BytesIO(response["Body"].read())) as image:
        thumbnail = ImageOps.exif_transpose(image)
        thumbnail.thumbnail((200, 200))
        thumbnail = thumbnail.convert("RGB")

        output = io.BytesIO()
        thumbnail.save(output, format="JPEG", quality=85)

        width, height = thumbnail.size

    output_key = f"thumbnails/{key}.jpg"

    s3.put_object(
        Bucket=DESTINATION_BUCKET,
        Key=output_key,
        Body=output.getvalue(),
        ContentType="image/jpeg",
    )

    return {
        "success": True,
        "bucket": DESTINATION_BUCKET,
        "key": output_key,
        "width": width,
        "height": height,
    }


def lambda_handler(event, context):
    if "Records" in event:
        results = []

        for record in event["Records"]:
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])

            try:
                results.append(resize_image(bucket, key))
            except Exception:
                logger.exception("S3 image processing failed")
                raise

        return {"success": True, "results": results}

    try:
        return resize_image(event["bucket"], event["key"])
    except Exception:
        logger.exception("Workflow image processing failed")
        return {
            "success": False,
            "error": "Image processing failed. Check CloudWatch logs.",
        }
