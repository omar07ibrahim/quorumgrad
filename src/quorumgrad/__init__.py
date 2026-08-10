"""QuorumGrad public package surface."""

from quorumgrad.engine import aggregate_document
from quorumgrad.errors import ContractError, QuorumGradError, VerificationError
from quorumgrad.verify import verify_receipt

__all__ = [
    "ContractError",
    "QuorumGradError",
    "VerificationError",
    "aggregate_document",
    "verify_receipt",
]
__version__ = "0.1.0"
