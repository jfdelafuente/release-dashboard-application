"""
Validation Result Model
Pydantic models for validation responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ValidationMetadata(BaseModel):
    """Metadata for validation result"""
    filename: str
    file_size: int
    file_size_formatted: str
    encoding_detected: str
    encoding_confidence: float = Field(ge=0, le=1)
    delimiter_detected: str
    headers: List[str]
    headers_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    warnings: List[str] = []


class ValidationError(BaseModel):
    """Individual validation error"""
    field: Optional[str] = None
    error: str
    message: str
    suggestion: Optional[str] = None


class ValidationResponse(BaseModel):
    """Full validation response"""
    success: bool
    message: str
    temp_file_path: Optional[str] = None
    metadata: Optional[ValidationMetadata] = None
    errors: List[ValidationError] = []
    warnings: List[str] = []


class ConfirmUploadRequest(BaseModel):
    """Request to confirm upload and move file"""
    temp_file_path: str
    filename: str
    metadata: Optional[Dict[str, Any]] = None


class ConfirmUploadResponse(BaseModel):
    """Response to confirm upload request"""
    success: bool
    message: str
    final_filename: str
    status: str = "processing"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
