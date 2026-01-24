class SpecValidationError(ValueError):
    """Raised when a spec fails validation or parsing."""


class DomainValidationError(ValueError):
    """Raised when derived domain constraints are violated."""
