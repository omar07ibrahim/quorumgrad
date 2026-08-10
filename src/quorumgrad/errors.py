"""Public QuorumGrad exception hierarchy."""


class QuorumGradError(Exception):
    """Base class for expected QuorumGrad failures."""


class ContractError(QuorumGradError, ValueError):
    """Raised when a round or bounded JSON document violates its contract."""


class VerificationError(QuorumGradError, ValueError):
    """Raised when a receipt cannot be independently replayed."""
