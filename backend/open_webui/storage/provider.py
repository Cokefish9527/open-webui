import os
import shutil
import json
import logging
import re
from abc import ABC, abstractmethod
from io import BytesIO
from typing import BinaryIO, Dict, Optional, Tuple

from open_webui.config.oss import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_KEY_PREFIX,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
    S3_USE_ACCELERATE_ENDPOINT,
    S3_ADDRESSING_STYLE,
    S3_ENABLE_TAGGING,
    GCS_BUCKET_NAME,
    GOOGLE_APPLICATION_CREDENTIALS_JSON,
    AZURE_STORAGE_ENDPOINT,
    AZURE_STORAGE_CONTAINER_NAME,
    AZURE_STORAGE_KEY,
    STORAGE_PROVIDER,
    UPLOAD_DIR,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class StorageProvider(ABC):
    @abstractmethod
    def get_file(self, file_path: str) -> str:
        pass

    @abstractmethod
    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        pass

    @abstractmethod
    def delete_all_files(self) -> None:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        pass

    def generate_download_url(self, file_path: str, expires: int = 900) -> Optional[str]:
        """默认返回 None，表示当前存储驱动不支持签名链接。"""
        return None


class LocalStorageProvider(StorageProvider):
    @staticmethod
    def upload_file(
        file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
        
        # 确保上传目录存在
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        file_path = f"{UPLOAD_DIR}/{filename}"
        
        # 确保文件路径的目录存在
        file_dir = os.path.dirname(file_path)
        if file_dir and not os.path.exists(file_dir):
            os.makedirs(file_dir, exist_ok=True)
        
        try:
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            raise RuntimeError(f"Failed to write file to local storage: {file_path}, error: {e}")
        
        return contents, file_path

    @staticmethod
    def get_file(file_path: str) -> str:
        """Handles downloading of the file from local storage."""
        return file_path

    @staticmethod
    def delete_file(file_path: str) -> None:
        """Handles deletion of the file from local storage."""
        filename = file_path.split("/")[-1]
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            log.warning(f"File {file_path} not found in local storage.")

    @staticmethod
    def delete_all_files() -> None:
        """Handles deletion of all files from local storage."""
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f"Failed to delete {file_path}. Reason: {e}")
        else:
            log.warning(f"Directory {UPLOAD_DIR} not found in local storage.")


# 只有在需要时才导入云存储相关的库
def get_s3_client():
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        
        config = Config(
            s3={
                "use_accelerate_endpoint": S3_USE_ACCELERATE_ENDPOINT,
                "addressing_style": S3_ADDRESSING_STYLE,
            },
        )

        # If access key and secret are provided, use them for authentication
        if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
            s3_client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                aws_access_key_id=S3_ACCESS_KEY_ID,
                aws_secret_access_key=S3_SECRET_ACCESS_KEY,
                config=config,
            )
        else:
            # If no explicit credentials are provided, fall back to default AWS credentials
            # This supports workload identity (IAM roles for EC2, EKS, etc.)
            s3_client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                config=config,
            )
        return s3_client, ClientError
    except ImportError:
        raise RuntimeError("boto3 library is required for S3 storage provider")


def get_gcs_client():
    try:
        from google.cloud import storage
        from google.cloud.exceptions import GoogleCloudError, NotFound
        
        if GOOGLE_APPLICATION_CREDENTIALS_JSON:
            gcs_client = storage.Client.from_service_account_info(
                info=json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
            )
        else:
            # if no credentials json is provided, credentials will be picked up from the environment
            # if running on local environment, credentials would be user credentials
            # if running on a Compute Engine instance, credentials would be from Google Metadata server
            gcs_client = storage.Client()
        return gcs_client, GoogleCloudError, NotFound
    except ImportError:
        raise RuntimeError("google-cloud-storage library is required for GCS storage provider")


def get_azure_client():
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ResourceNotFoundError
        
        endpoint = AZURE_STORAGE_ENDPOINT
        container_name = AZURE_STORAGE_CONTAINER_NAME
        storage_key = AZURE_STORAGE_KEY

        if storage_key:
            # Configure using the Azure Storage Account Endpoint and Key
            blob_service_client = BlobServiceClient(
                account_url=endpoint, credential=storage_key
            )
        else:
            # Configure using the Azure Storage Account Endpoint and DefaultAzureCredential
            # If the key is not configured, then the DefaultAzureCredential will be used to support Managed Identity authentication
            blob_service_client = BlobServiceClient(
                account_url=endpoint, credential=DefaultAzureCredential()
            )
        container_client = blob_service_client.get_container_client(container_name)
        return blob_service_client, container_client, ResourceNotFoundError
    except ImportError:
        raise RuntimeError("azure-storage-blob library is required for Azure storage provider")


class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.s3_client, self.ClientError = get_s3_client()
        self.bucket_name = S3_BUCKET_NAME
        self.key_prefix = S3_KEY_PREFIX if S3_KEY_PREFIX else ""

    @staticmethod
    def sanitize_tag_value(s: str) -> str:
        """Only include S3 allowed characters."""
        return re.sub(r"[^a-zA-Z0-9 äöüÄÖÜß\+\-=\._:/@]", "", s)

    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to S3 storage."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        s3_key = os.path.join(self.key_prefix, filename)
        try:
            extra_args = {}
            if S3_ENABLE_TAGGING and tags:
                sanitized_tags = {
                    self.sanitize_tag_value(k): self.sanitize_tag_value(v)
                    for k, v in tags.items()
                }
                if sanitized_tags:
                    extra_args["Tagging"] = "&".join(
                        f"{k}={v}" for k, v in sanitized_tags.items()
                    )
            self.s3_client.upload_fileobj(
                BytesIO(contents),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args or None,
            )
            return contents, f"s3://{self.bucket_name}/{s3_key}"
        except self.ClientError as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            local_file_path = self._get_local_file_path(s3_key)
            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            return local_file_path
        except self.ClientError as e:
            raise RuntimeError(f"Error downloading file from S3: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except self.ClientError as e:
            raise RuntimeError(f"Error deleting file from S3: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from S3 storage."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if "Contents" in response:
                for content in response["Contents"]:
                    # Skip objects that were not uploaded from open-webui in the first place
                    if not content["Key"].startswith(self.key_prefix):
                        continue

                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=content["Key"]
                    )
        except self.ClientError as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()

    def generate_download_url(self, file_path: str, expires: int = 900) -> Optional[str]:
        try:
            s3_key = self._extract_s3_key(file_path)
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires,
            )
        except self.ClientError as e:
            raise RuntimeError(f"Error generating presigned URL: {e}")

    # The s3 key is the name assigned to an object. It excludes the bucket name, but includes the internal path and the file name.
    def _extract_s3_key(self, full_file_path: str) -> str:
        return "/".join(full_file_path.split("//")[1].split("/")[1:])

    def _get_local_file_path(self, s3_key: str) -> str:
        return f"{UPLOAD_DIR}/{s3_key.split('/')[-1]}"


class GCSStorageProvider(StorageProvider):
    def __init__(self):
        self.gcs_client, self.GoogleCloudError, self.NotFound = get_gcs_client()
        self.bucket_name = GCS_BUCKET_NAME
        self.bucket = self.gcs_client.bucket(GCS_BUCKET_NAME)

    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to GCS storage."""
        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        try:
            blob = self.bucket.blob(filename)
            blob.upload_from_filename(file_path)
            return contents, "gs://" + self.bucket_name + "/" + filename
        except self.GoogleCloudError as e:
            raise RuntimeError(f"Error uploading file to GCS: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from GCS storage."""
        try:
            filename = file_path.removeprefix("gs://").split("/")[1]
            local_file_path = f"{UPLOAD_DIR}/{filename}"
            blob = self.bucket.get_blob(filename)
            blob.download_to_filename(local_file_path)

            return local_file_path
        except self.NotFound as e:
            raise RuntimeError(f"Error downloading file from GCS: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from GCS storage."""
        try:
            filename = file_path.removeprefix("gs://").split("/")[1]
            blob = self.bucket.get_blob(filename)
            blob.delete()
        except self.NotFound as e:
            raise RuntimeError(f"Error deleting file from GCS: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from GCS storage."""
        try:
            blobs = self.bucket.list_blobs()

            for blob in blobs:
                blob.delete()

        except self.NotFound as e:
            raise RuntimeError(f"Error deleting all files from GCS: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()


class AzureStorageProvider(StorageProvider):
    def __init__(self):
        self.blob_service_client, self.container_client, self.ResourceNotFoundError = get_azure_client()
        self.endpoint = AZURE_STORAGE_ENDPOINT
        self.container_name = AZURE_STORAGE_CONTAINER_NAME

    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to Azure Blob Storage."""
        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        try:
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.upload_blob(contents, overwrite=True)
            return contents, f"{self.endpoint}/{self.container_name}/{filename}"
        except Exception as e:
            raise RuntimeError(f"Error uploading file to Azure Blob Storage: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from Azure Blob Storage."""
        try:
            filename = file_path.split("/")[-1]
            local_file_path = f"{UPLOAD_DIR}/{filename}"
            blob_client = self.container_client.get_blob_client(filename)
            with open(local_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            return local_file_path
        except self.ResourceNotFoundError as e:
            raise RuntimeError(f"Error downloading file from Azure Blob Storage: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from Azure Blob Storage."""
        try:
            filename = file_path.split("/")[-1]
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.delete_blob()
        except self.ResourceNotFoundError as e:
            raise RuntimeError(f"Error deleting file from Azure Blob Storage: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from Azure Blob Storage."""
        try:
            blobs = self.container_client.list_blobs()
            for blob in blobs:
                self.container_client.delete_blob(blob.name)
        except Exception as e:
            raise RuntimeError(f"Error deleting all files from Azure Blob Storage: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()


def get_storage_provider(storage_provider: str):
    if storage_provider == "local":
        Storage = LocalStorageProvider()
    elif storage_provider == "s3":
        Storage = S3StorageProvider()
    elif storage_provider == "gcs":
        Storage = GCSStorageProvider()
    elif storage_provider == "azure":
        Storage = AzureStorageProvider()
    else:
        raise RuntimeError(f"Unsupported storage provider: {storage_provider}")
    return Storage


Storage = get_storage_provider(STORAGE_PROVIDER)
