from __future__ import annotations


class ServiceError(RuntimeError):
    """Base exception for service-layer failures."""


class ExternalDependencyError(ServiceError):
    """Raised when a local model, network service, or credential-backed service fails."""
