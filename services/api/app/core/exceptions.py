class AppError(Exception):
    """Base application error."""


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""


class ConflictError(AppError):
    """Raised when a write would violate a uniqueness or state rule."""


class ForbiddenError(AppError):
    """Raised when the current actor is not allowed to perform an action."""


class ServiceUnavailableError(AppError):
    """Raised when a required internal dependency is unavailable."""
