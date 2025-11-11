import logging
from dataclasses import dataclass
from typing import List, Optional

from open_webui.config.oss import S3_BUCKET_NAME, S3_KEY_PREFIX, STORAGE_PROVIDER
from open_webui.storage.provider import get_s3_client

log = logging.getLogger(__name__)


@dataclass
class OSSObjectSummary:
    key: str
    size: int
    last_modified: Optional[int]


class OSSMaterialRepository:
    """Thin wrapper around the S3 client for listing objects under company/scene prefixes."""

    def __init__(self) -> None:
        if STORAGE_PROVIDER.lower() != "s3":
            raise RuntimeError("OSSMaterialRepository requires STORAGE_PROVIDER=s3")
        self.client, self.ClientError = get_s3_client()
        self.bucket = S3_BUCKET_NAME
        self.prefix = (S3_KEY_PREFIX or "").strip()

    def list_relative_objects(self, relative_prefix: str) -> List[OSSObjectSummary]:
        """Return object summaries whose key starts with the given relative prefix."""

        if not self.bucket:
            log.warning("S3 bucket name is empty; returning no objects")
            return []

        full_prefix = self._build_full_prefix(relative_prefix)
        continuation_token: Optional[str] = None
        objects: List[OSSObjectSummary] = []

        while True:
            try:
                params = {"Bucket": self.bucket, "Prefix": full_prefix}
                if continuation_token:
                    params["ContinuationToken"] = continuation_token
                response = self.client.list_objects_v2(**params)
            except self.ClientError as exc:  # pragma: no cover - network failure
                log.error("Failed to list OSS prefix %s: %s", full_prefix, exc)
                return []

            for item in response.get("Contents", []):
                relative_key = self._strip_prefix(item["Key"])
                last_modified = item.get("LastModified")
                epoch = int(last_modified.timestamp()) if last_modified else None
                objects.append(
                    OSSObjectSummary(
                        key=relative_key,
                        size=int(item.get("Size") or 0),
                        last_modified=epoch,
                    )
                )

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")

        return objects

    def _build_full_prefix(self, relative_prefix: str) -> str:
        cleaned_relative = relative_prefix.lstrip("/")
        if not self.prefix:
            return cleaned_relative
        cleaned_prefix = self.prefix.rstrip("/")
        return f"{cleaned_prefix}/{cleaned_relative}" if cleaned_relative else cleaned_prefix

    def _strip_prefix(self, key: str) -> str:
        if not self.prefix:
            return key
        cleaned_prefix = self.prefix.rstrip("/")
        if key.startswith(f"{cleaned_prefix}/"):
            return key[len(cleaned_prefix) + 1 :]
        return key
