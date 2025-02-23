from io import BytesIO

from fastapi import Depends
from types_aiobotocore_s3 import S3Client

from app.core.aws_boto_clients import get_s3_client
from app.core.config import get_settings, Settings


class S3Storage:
    def __init__(
        self,
        client: S3Client = Depends(get_s3_client),
        settings: Settings = Depends(get_settings),
    ):
        self._bucket_name = settings.S3_BUCKET
        self._client = client
        self._paginator = self._client.get_paginator('list_objects_v2')

    async def upload_result_datafile(self) -> None:
        test_content = b'Hello World'
        await self._client.put_object(
            Bucket=self._bucket_name,
            Key='1',
            Body=BytesIO(test_content),
        )

    async def list_keys(self, bucket_name: str, prefix: str = '') -> list[str]:
        keys: list[str] = []
        async for page in self._paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for content in page.get('Contents', ()):
                keys.append(content['Key'])
        return keys
