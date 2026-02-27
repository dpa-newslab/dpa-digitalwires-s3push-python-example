import json
import logging
import os
from os.path import basename
from urllib.parse import urlparse

import boto3
from boto3.s3.transfer import TransferConfig
from iptc7901 import convert_to_iptc
from newsmlg2 import convert_to_g2
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logging.getLogger().setLevel(logging.INFO)

s3 = boto3.client("s3")

S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
PREFIX_OUT = os.environ["S3_BUCKET_PREFIX_OUT"]
PREFIX_TO_REMOVE = os.environ["S3_BUCKET_PREFIX_TO_REMOVE"]
DOWNLOAD_ASSETS = os.environ["DOWNLOAD_ASSETS"].lower() == "true"
CONVERT_TO_IPTC = os.environ["CONVERT_TO_IPTC"].lower() == "true"
CONVERT_TO_NEWSMLG2 = os.environ["CONVERT_TO_NEWSMLG2"].lower() == "true"


def receive_digitalwires(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"])

        entries = body.get("Records", [])
        for entry in entries:
            bucket_name = entry["s3"]["bucket"]["name"]
            object_key = entry["s3"]["object"]["key"]

            resp = s3.get_object(Bucket=bucket_name, Key=object_key)

            entry = json.loads(resp["Body"].read())

            entry_name = object_key.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[
                0
            ]
            base_entry_key = f"{PREFIX_OUT}/{entry_name}"

            put_object(
                bucket=S3_BUCKET_NAME,
                key=f"{base_entry_key}/digitalwire.json",
                content=json.dumps(entry),
            )

            if DOWNLOAD_ASSETS:
                download_assets(base_entry_key, entry)

            if CONVERT_TO_IPTC:
                iptcs = convert_to_iptc(entry)
                logging.info(f"created {len(iptcs)} iptc entries")
                for service, iptc in iptcs.items():
                    iptc_key = f"{base_entry_key}/{service.split(':')[-1]}.iptc"
                    put_object(
                        bucket=S3_BUCKET_NAME,
                        key=iptc_key,
                        content=iptc,
                        content_type="text/plain",
                    )

            if CONVERT_TO_NEWSMLG2:
                g2 = convert_to_g2(entry)
                g2_key = f"{base_entry_key}/newsmlg2.xml"
                logging.info("created g2 entry")
                put_object(
                    bucket=S3_BUCKET_NAME,
                    key=g2_key,
                    content=g2,
                    content_type="application/xml",
                )

            logging.info(f"Saved to '{base_entry_key}'")


def session_with_exponential_backoff():
    """Session with retry and exponential backoff for fetching assets"""
    s = Session()
    retry = Retry(
        total=3,
        status_forcelist=[404, 429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        backoff_factor=1,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def download_assets(base_entry_key, entry):
    with session_with_exponential_backoff() as s:
        for assoc in entry.get("associations", []):
            for rendition in assoc.get("renditions", []):
                if rendition.get("url") is None:
                    logging.warning(f"warning: missing url for rendition {rendition}")
                    continue

                file_extension = basename(urlparse(rendition["url"]).path).split(".")[
                    -1
                ]
                urn = assoc["urn"].replace(":", "_")
                outfile = (
                    basename(urlparse(rendition["url"]).path)
                    or f"{urn}-s{rendition.get('size',  'default')}.{file_extension}"
                )
                outpath = f"{base_entry_key}/{outfile}"
                r = s.get(rendition["url"], stream=True)
                r.raise_for_status()

                put_asset(S3_BUCKET_NAME, outpath, r)


def put_asset(bucket, key, response):
    s3.upload_fileobj(
        response.raw,
        bucket,
        key,
        Config=TransferConfig(
            multipart_threshold=1024 * 1024 * 5,
            multipart_chunksize=1024 * 1024 * 5,
            use_threads=False,
        ),
    )


def put_object(bucket, key, content, content_type="application/json"):
    s3.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
