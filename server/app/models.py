from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.internal.db import Base


class Document(Base):
    """
    Document main table - stores basic document information and metadata
    
    Why separate Document and DocumentVersion?
    - Document: stores basic document information (title, current version, etc.)
    - DocumentVersion: stores specific content for each version
    This design makes version management clearer and facilitates future feature extensions
    """
    __tablename__ = "document"
    
    # Primary key ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Document title - user-friendly document name
    title = Column(String, nullable=False, default="Untitled Document")
    
    # Current active version ID - points to the version user is currently viewing/editing
    current_version_id = Column(Integer, ForeignKey("document_version.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship definition - SQLAlchemy ORM functionality
    # back_populates creates bidirectional relationship, allows access to versions from Document and document from Version
    # foreign_keys explicitly specifies which foreign key to use for this relationship, avoiding ambiguity
    versions = relationship(
        "DocumentVersion", 
        back_populates="document", 
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id"  # Explicitly specify foreign key
    )
    
    # Current version relationship - separately defined for quick access to current version
    current_version = relationship(
        "DocumentVersion", 
        foreign_keys=[current_version_id], 
        post_update=True
    )


class DocumentVersion(Base):
    """
    Document version table - stores specific content and version information for each version
    
    Why need version_number?
    - Version number shown to users (v1.0, v2.0, etc.)
    - More friendly and meaningful than database ID
    
    Why need is_active?
    - Mark which version is the currently active version
    - Allow users to switch between different versions
    """
    __tablename__ = "document_version"
    
    # Primary key ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key - associate to which document
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False, index=True)
    
    # Version number - increment from 1 (v1.0, v2.0...)
    version_number = Column(Integer, nullable=False)
    
    # Version content - actual document content for this version
    content = Column(String, nullable=False, default="")
    
    # Whether this is the current active version
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Creation time - record when this version was created
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship definition - reverse relationship to Document
    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])


# Include your models here, and they will automatically be created as tables in the database on start-up
