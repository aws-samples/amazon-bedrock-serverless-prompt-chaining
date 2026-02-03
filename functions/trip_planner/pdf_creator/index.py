from md2pdf.core import md2pdf
import os
import tempfile
import uuid
import boto3

s3_client = boto3.client("s3")
s3_bucket_name = os.environ.get("PDF_BUCKET")


def handler(event, context):
    location = event["location"]
    itinerary_content = f"""
# Your Weekend Vacation

Here is your three day itinerary for your visit to {location}, created by generative AI.  Enjoy!

{event["itinerary"]}
"""

    s3_object_key = f"itinerary-{uuid.uuid4()}.pdf"

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_tmp:
        pdf_tmp_path = pdf_tmp.name

    try:
        md2pdf(
            pdf_tmp_path,
            raw=itinerary_content,
        )

        s3_client.upload_file(
            pdf_tmp_path,
            s3_bucket_name,
            s3_object_key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
    finally:
        if os.path.exists(pdf_tmp_path):
            os.unlink(pdf_tmp_path)

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": s3_bucket_name, "Key": s3_object_key},
        ExpiresIn=900,  # 15 minutes
    )

    return {
        "itinerary_url": url,
        "location": location,
    }
