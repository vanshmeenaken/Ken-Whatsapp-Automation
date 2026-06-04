"""
Message Request/Response Schemas
Pydantic models for API validation
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, Any
from datetime import datetime


class SendRequest(BaseModel):
    """Schema for sending a single message."""
    
    phone_number: str = Field(..., description="Recipient phone number in E.164 format")
    message: str = Field(..., min_length=1, max_length=4096, description="WhatsApp message text")
    template_variables: Optional[Dict[str, str]] = Field(
        None, 
        description="Variables to substitute in message template"
    )

    @validator('phone_number')
    def validate_phone(cls, v):
        # Basic validation - regex will be more thorough in agent
        if not v or len(v) < 10:
            raise ValueError('Invalid phone number format')
        return v


class SendResponse(BaseModel):
    """Schema for send response."""
    
    success: bool
    message_id: Optional[str] = None
    phone_number: str
    sent_at: Optional[str] = None
    status: str  # sent | failed
    error: Optional[str] = None
    error_code: Optional[str] = None


class BatchUploadRequest(BaseModel):
    """Schema for batch upload request."""
    
    csv_content: str = Field(..., description="CSV file content as string")
    # Format expected: phone_number,first_name,company,message_template


class MessageLog(BaseModel):
    """Schema for message log entry."""
    
    message_id: str
    phone_number: str
    text: str
    status: str  # sent | delivered | failed | read
    sent_at: str
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None


class FetchResponse(BaseModel):
    """Schema for fetch messages response."""
    
    success: bool
    messages: list[MessageLog]
    total_count: int
    limit: int
    offset: int
    has_more: bool
