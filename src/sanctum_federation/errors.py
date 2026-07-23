class SanctumFederationError(ValueError):
    """A federation input, runtime state, or output is not trustworthy."""


class DispatchExecutionError(RuntimeError):
    """A selected minister could not be executed."""
