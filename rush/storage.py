"""
Custom storage backends for RUSH application.
"""

from enum import Enum
from typing import IO, Any

from django.conf import settings
from storages.backends.s3 import S3Storage


class BackblazeStorageFactory:
    """
    A Django-compatible storage factory for Backblaze that automatically connects the storage objects
    to backblaze using the app id, app key id, endpoint url, and region name in `settings.py`.
    """

    class Visibility(Enum):
        ANY = "any"
        PUBLIC = "public"
        PRIVATE = "private"

    class UnexpectedVisibility(Exception):
        """
        The bucket's visibility in Backblaze was not as expected.
        """

        def __init__(
            self,
            bucket_name: str,
            expected: "BackblazeStorageFactory.Visibility",
            actual: "BackblazeStorageFactory.Visibility",
        ):
            super().__init__(
                "Expected bucket '{}' to have visibility {}, but instead it was {}.".format(
                    bucket_name,
                    expected.name,
                    actual.name,
                )
            )

    class Persistance(Enum):
        HARD_DELETE = "hard_delete"
        USE_BUCKET_SETTINGS = "use_bucket_settings"

    class Duplication(Enum):
        LATEST_VERSION_ONLY = "latest_version_only"
        USE_BUCKET_SETTINGS = "use_bucket_settings"

    _storage_instances = dict()  # keys are the bucket names

    @classmethod
    def create_from_bucket_name(
        cls,
        bucket_name: str,
        validate_visibility=Visibility.ANY,
        persistance=Persistance.USE_BUCKET_SETTINGS,
        duplication=Duplication.USE_BUCKET_SETTINGS,
    ) -> S3Storage:
        """
        Create a Django-compatible S3Storage object for Backblaze by specifying a bucket name.
        Raise `UnexpectedVisibility` if the bucket's visibility does not match `validate_visibility`.
        Hard-deletes objects on remote if `persistance` is set to `Persistance.HARD_DELETE`.
        Only keeps the latest version of a file if `dupliation` is set to `Duplication.LATEST_VERSION_ONLY`.
        """
        if bucket_name not in cls._storage_instances:
            storage = S3Storage(
                default_acl="public-read",
                # Includes auth creds in Django FileField's urls when True. Not needed if bucket is public.
                querystring_auth=False if validate_visibility == cls.Visibility.PUBLIC else True,
                access_key=settings.BACKBLAZE_APP_KEY_ID,
                secret_key=settings.BACKBLAZE_APP_KEY,
                endpoint_url=settings.BACKBLAZE_ENDPOINT_URL,
                region_name=settings.BACKBLAZE_REGION_NAME,
                bucket_name=bucket_name,
            )
            bucket = storage.bucket
            is_public = cls._is_bucket_public(bucket)
            if validate_visibility == cls.Visibility.PUBLIC and not is_public:
                raise cls.UnexpectedVisibility(
                    bucket_name,
                    expected=cls.Visibility.PUBLIC,
                    actual=cls.Visibility.PRIVATE,
                )
            elif validate_visibility == cls.Visibility.PRIVATE and is_public:
                raise cls.UnexpectedVisibility(
                    bucket_name,
                    expected=cls.Visibility.PRIVATE,
                    actual=cls.Visibility.PUBLIC,
                )
            if persistance == cls.Persistance.HARD_DELETE:
                storage.delete = cls._make_hard_delete_fn(bucket)
            if duplication == cls.Duplication.LATEST_VERSION_ONLY:
                storage.save = cls._make_override_previous_save_fn(bucket, storage.save)
            cls._storage_instances[bucket_name] = storage
        return cls._storage_instances[bucket_name]

    @classmethod
    def _make_hard_delete_fn(cls, bucket):
        """
        Delete all versions of the file with the given name.
        """

        def hard_delete_fn(name: str) -> None:
            if name:
                versions = bucket.object_versions.filter(Prefix=name)
                for version in versions:
                    version.delete()

        return hard_delete_fn

    @classmethod
    def _make_override_previous_save_fn(cls, bucket, original_save):
        """
        Delete all previous versions of a file when saving.
        """

        def save_fn(name: str | None, content: IO[Any], max_length: int | None = None) -> str:
            result = original_save(name, content, max_length)
            versions = list(bucket.object_versions.filter(Prefix=name))
            if len(versions) > 1:
                versions.sort(key=lambda v: v.last_modified, reverse=True)
                for old_version in versions[1:]:
                    # delete all versions except the latest
                    old_version.delete()

            return result

        return save_fn

    @classmethod
    def _is_bucket_public(
        cls,
        bucket,
    ) -> bool:
        acl = bucket.Acl()
        grants = acl.grants
        is_public = any(
            grant.get("Grantee", {}).get("URI") == "http://acs.amazonaws.com/groups/global/AllUsers"
            and grant.get("Permission") in ["READ", "FULL_CONTROL"]
            for grant in grants
        )
        return is_public
