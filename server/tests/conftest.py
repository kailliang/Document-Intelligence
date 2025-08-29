"""
Pytest configuration and fixtures for the Document Intelligence test suite.
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add server directory to Python path
import sys
server_dir = Path(__file__).parent.parent
sys.path.insert(0, str(server_dir))

from app.internal.db import Base
from app.models import Document, DocumentVersion, ChatHistory
from app.__main__ import app


@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine using SQLite in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:", 
        echo=False,
        # Enable foreign key constraints in SQLite
        connect_args={"check_same_thread": False}
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        # Clean up all data after each test
        session.rollback()
        session.close()
        
        # Clear all data from tables to ensure isolation
        # Use a fresh connection to avoid transaction conflicts
        with test_db_engine.begin() as conn:
            # Disable foreign key constraints temporarily for cleanup
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            
            # Delete in dependency order (child tables first)
            conn.execute(text("DELETE FROM chat_history"))
            conn.execute(text("DELETE FROM document_version")) 
            conn.execute(text("DELETE FROM document"))
            
            # Re-enable foreign key constraints
            conn.execute(text("PRAGMA foreign_keys = ON"))
            
            # Reset auto-increment sequences if table exists
            try:
                conn.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('document', 'document_version', 'chat_history')"))
            except Exception:
                # sqlite_sequence table may not exist in in-memory databases
                pass


@pytest.fixture
def client():
    """Create a test client for FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_document(db_session):
    """Create a sample document with version for testing."""
    # Create document (let SQLite assign ID automatically)
    doc = Document(
        title="Test Document",
    )
    db_session.add(doc)
    db_session.flush()
    
    # Create version
    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        content="<h1>Test Document</h1><p>This is a test document content.</p>",
        is_active=True
    )
    db_session.add(version)
    db_session.flush()
    
    # Update document's current version
    doc.current_version_id = version.id
    db_session.flush()
    
    return doc


@pytest.fixture
def sample_chat_history(db_session, sample_document):
    """Create sample chat history for testing."""
    chat1 = ChatHistory.create_user_message(
        document_id=sample_document.id,
        version_number="v1.0",
        content="Please analyze this document"
    )
    chat2 = ChatHistory.create_assistant_message(
        document_id=sample_document.id,
        version_number="v1.0",
        content="I found 3 suggestions for improvement.",
        agents_used=["technical", "legal"]
    )
    
    db_session.add(chat1)
    db_session.add(chat2)
    db_session.commit()
    
    return [chat1, chat2]


@pytest.fixture
def mock_ai_response():
    """Mock AI response for testing."""
    return {
        "issues": [
            {
                "type": "Structure & Punctuation",
                "severity": "high",
                "paragraph": 1,
                "description": "Missing colon after claim number",
                "originalText": "1. A method comprising",
                "replaceTo": "1. A method comprising:",
                "confidence": 0.95
            }
        ]
    }


@pytest.fixture
def temp_export_dir():
    """Create temporary directory for PDF export tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "exports"
        export_path.mkdir()
        yield export_path