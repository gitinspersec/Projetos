"""
ⒸAngelaMos | 2026
exceptions.py

Custom exception hierarchy for network traffic analyzer

All exceptions inherit from NetAnalError, which inherits from Exception.
This lets callers catch all tool errors with a single except clause while
still being able to handle specific failure modes separately.

Key exports:
  NetAnalError - Base class for all tool exceptions
  CaptureError - General capture failure
  CapturePermissionError - User lacks privileges for packet capture
  NpcapNotFoundError - Npcap not installed on Windows
  InvalidFilterError - Malformed BPF filter expression
  ExportError - Failure when writing export files
  AnalysisError - Failure during packet analysis
  ValidationError - Invalid input values (ports, IPs, networks)

Connects to:
  filters.py - raises ValidationError for invalid inputs
  __init__.py - re-exports all exceptions to the public API
"""


class NetAnalError(Exception):
    """
    Base exception for all netanal errors
    """


class CaptureError(NetAnalError):
    """
    Errors related to packet capture operations
    """


class CapturePermissionError(CaptureError):
    """
    Insufficient permissions for packet capture
    """


class NpcapNotFoundError(CaptureError):
    """
    Npcap is not installed on Windows
    """


class InvalidFilterError(NetAnalError):
    """
    Invalid BPF filter expression
    """


class ExportError(NetAnalError):
    """
    Errors during data export operations
    """


class AnalysisError(NetAnalError):
    """
    Errors during packet analysis
    """


class ValidationError(NetAnalError):
    """
    Input validation errors
    """


__all__ = [
    "AnalysisError",
    "CaptureError",
    "CapturePermissionError",
    "ExportError",
    "InvalidFilterError",
    "NetAnalError",
    "NpcapNotFoundError",
    "ValidationError",
]
