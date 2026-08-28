import mimetypes
from dataclasses import dataclass
from typing import List

from django.core.exceptions import ValidationError
from django.db import models


@dataclass
class GuessedMimeType:
    """
    Represents a guessed mime-type for a specific file and provides a validation function.
    This "extra" class was made to avoid associating the MimeType model with a filename. A guess
    of a mimetype is instead associated with a filename and can be validated against other mimetypes.
    """

    filename: str
    guessed: "MimeType"

    class BaseValidationError(ValidationError):
        """
        Base exception class for when a guessed mime-type is invalid.
        """

        ...

    class Unknown(BaseValidationError):
        """
        The mimetype of a file is unknown, or could not be parsed.
        """

        def __init__(self, filename: str):
            super().__init__("The mimetype of file '{}' could not be parsed.".format(filename))

    class Unsupported(BaseValidationError):
        """
        The mimetype exists according to Python's `mimetypes` module,
        but is currently unsupported by the RUSH app.
        """

        def __init__(self, filename: str, valid: List["MimeType"], invalid: List["MimeType"]):
            super().__init__(
                "The mimetype of file '{}' is currently not supported. Allowed types: {}. Disallowed types: {}.".format(
                    filename,
                    [x.human_name for x in valid],
                    [x.human_name for x in invalid],
                )
            )

    class Invalid(BaseValidationError):
        """
        The mimetype is both known and supported by the system, but is an
        invalid type for the file at validation-time.
        """

        def __init__(self, mimetype: "MimeType", filename: str, valid: List["MimeType"], invalid: List["MimeType"]):
            super().__init__(
                "The mimetype {} is invalid for file {}. Allowed types: {}. Disallowed types: {}.".format(
                    mimetype.human_name,
                    filename,
                    [x.human_name for x in valid],
                    [x.human_name for x in invalid],
                )
            )

    def validate(
        self,
        valid: List["MimeType"] | None = None,
        invalid: List["MimeType"] | None = None,
    ) -> None:
        """
        Raise a validation-error if this mimetype isn't a member of `valid`, or is a member of `invalid`.
        """
        valid = [] if valid is None else valid
        invalid = [] if invalid is None else invalid
        if self.guessed == MimeType.UNKNOWN():
            raise self.Unknown(self.filename)
        elif self.guessed == MimeType.UNSUPPORTED():
            raise self.Unsupported(self.filename, valid, invalid)
        elif valid != [] and self.guessed not in valid or self.guessed in invalid:
            # when valid list is not empty, guessed must be in there
            raise self.Invalid(self.guessed, self.filename, valid, invalid)
        elif valid == [] and self.guessed in invalid:
            # when valid list is empty, guessed doesn't need to be in there, it only
            # needs to be missing from the invalid list.
            raise self.Invalid(self.guessed, self.filename, valid, invalid)


class MimeType(models.Model):
    """
    The media type of a file, see: https://en.wikipedia.org/wiki/Media_type.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["_values"],
                condition=models.Q(is_valid=True),
                name="unique_mimetype_value_when_valid",
            ),
        ]

    human_name = models.CharField(max_length=255)
    _values = models.CharField(max_length=255)
    is_valid = models.BooleanField(default=True)

    @property
    def values(self) -> List[str]:
        vals = self._values.split(",")
        return [x.strip() for x in vals]

    @classmethod
    def by_name(cls, mimetype_human_name: str) -> "MimeType":
        """
        Get a mimetype by it's human-readable name. Return the
        UNSUPPORTED mimetype if the name could not be found.
        """
        try:
            return cls.objects.get(human_name=mimetype_human_name)
        except cls.DoesNotExist:
            return cls.UNSUPPORTED()

    @classmethod
    def UNKNOWN(cls) -> "MimeType":
        return cls.objects.get(human_name="UNKNOWN")

    @classmethod
    def UNSUPPORTED(cls) -> "MimeType":
        return cls.objects.get(human_name="UNSUPPORTED")

    @classmethod
    def guess(cls, filename: str) -> GuessedMimeType:
        """
        Guess the mime-type based on a file name.
        """
        mime_type_value, encoding = mimetypes.guess_type(filename)
        if not mime_type_value:
            # unrecognized by mimetypes package... no idea what kind of file this is.
            return GuessedMimeType(filename, cls.UNKNOWN())
        try:
            # try to return an existing mimetype guess from our database.
            existing_type = cls.objects.get(_values__contains=mime_type_value)
            return GuessedMimeType(filename, existing_type)
        except MimeType.DoesNotExist:
            return GuessedMimeType(filename, cls.UNSUPPORTED())

    def __str__(self):
        return "{}-{}".format(
            self.human_name,
            self.values,
        )
