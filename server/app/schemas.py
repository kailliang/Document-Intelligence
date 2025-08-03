from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional


# ===================================================================
# DocumentVersion related Pydantic schemas
# ===================================================================

class DocumentVersionBase(BaseModel):
    """
    DocumentVersion base schema - contains basic version information
    
    Why separate Base, Create, Read schemas?
    - Base: common fields, other schemas inherit from it
    - Create: fields needed when creating version
    - Read: fields returned when reading from database (includes ID, timestamps, etc.)
    """
    content: str
    version_number: int


class DocumentVersionCreate(DocumentVersionBase):
    """Schema used when creating new version"""
    pass


class DocumentVersionRead(DocumentVersionBase):
    """Schema returned when reading version from database"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    document_id: int
    is_active: bool
    created_at: datetime


# ===================================================================
# Document related Pydantic schemas
# ===================================================================

class DocumentBase(BaseModel):
    """Document base schema"""
    title: str


class DocumentCreate(DocumentBase):
    """Schema used when creating new document"""
    pass


class DocumentRead(DocumentBase):
    """
    Schema returned when reading document from database
    
    Why include versions?
    - Allow frontend to get all version history of the document
    - Optional[List[...]] indicates optional version list
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    current_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # List containing all versions - for version history display
    versions: Optional[List[DocumentVersionRead]] = []
    
    # Detailed information of current active version
    current_version: Optional[DocumentVersionRead] = None


# ===================================================================
# Dedicated schemas for API requests/responses
# ===================================================================

class DocumentWithCurrentVersion(BaseModel):
    """
    Dedicated schema for returning document and its current version content
    This schema is specifically for editor, only returns necessary information
    """
    id: int
    title: str
    content: str  # Current version content
    version_number: int  # Current version number
    last_modified: datetime


class CreateVersionRequest(BaseModel):
    """Request schema for creating new version - content is now optional, new version defaults to empty"""
    content: Optional[str] = ""


class SwitchVersionRequest(BaseModel):
    """Request schema for switching version"""
    version_number: int
