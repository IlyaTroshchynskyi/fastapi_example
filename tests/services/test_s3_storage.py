from types_aiobotocore_s3 import S3Client

from app.core.config import get_settings
from app.core.services.s3_storage import S3Storage


class TestS3Storage:
    async def test_success(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success2(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success3(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success4(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success5(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success6(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success7(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success8(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success9(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)

    async def test_success10(self, s3_client: S3Client) -> None:
        settings = get_settings()
        s3 = S3Storage(s3_client, settings)
        await s3.upload_result_datafile()

        assert ['1'] == await s3.list_keys(settings.S3_BUCKET)
