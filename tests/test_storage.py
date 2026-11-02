import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

import storage


class FakeS3:
    def __init__(self, error=None):
        self.error = error
        self.uploads = []

    def put_object(self, **upload):
        if self.error:
            raise self.error
        self.uploads.append(upload)


@pytest.fixture
def local_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LOCAL_DIR", tmp_path)
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    return tmp_path


def test_successful_upload_uses_the_cloud(local_dir, monkeypatch):
    s3 = FakeS3()
    monkeypatch.setattr(storage, "create_s3_client", lambda: s3)

    location = storage.save_artifact("run1", "report.md", "hello")

    assert location == "s3://test-bucket/reports/run1/report.md"
    assert s3.uploads == [
        {"Bucket": "test-bucket", "Key": "reports/run1/report.md", "Body": b"hello"}
    ]
    assert not list(local_dir.iterdir())


@pytest.mark.parametrize(
    "error",
    [
        NoCredentialsError(),
        EndpointConnectionError(endpoint_url="https://example.com"),
        ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "PutObject"),
    ],
)
def test_any_upload_failure_falls_back_to_local(local_dir, monkeypatch, error):
    monkeypatch.setattr(storage, "create_s3_client", lambda: FakeS3(error))

    location = storage.save_artifact("run1", "report.md", "hello ₹")

    assert location == str(local_dir / "reports" / "run1" / "report.md")
    assert (local_dir / "reports" / "run1" / "report.md").read_text(encoding="utf-8") == "hello ₹"


def test_disk_failure_does_not_raise(monkeypatch):
    def broken_save(run_id, filename, content):
        raise OSError("disk full")

    monkeypatch.setattr(storage, "save_artifact", broken_save)

    assert storage.save_run("run1", {"report.md": "hello"}) == {}
