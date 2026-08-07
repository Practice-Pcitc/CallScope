from enum import StrEnum


class ProjectScanStatus(StrEnum):
    NOT_SCANNED = "NOT_SCANNED"
    SCANNING = "SCANNING"
    READY = "READY"
    FAILED = "FAILED"


class ScanTaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ScanStage(StrEnum):
    DISCOVERY = "DISCOVERY"
    VALIDATE = "VALIDATE"
    PARSE = "PARSE"
    RESOLVE = "RESOLVE"
    PERSIST = "PERSIST"
    COMPLETED = "COMPLETED"
