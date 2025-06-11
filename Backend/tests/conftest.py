"""
Pytest configuration and fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for testing."""
    return engine


@pytest.fixture(scope="session")
def db_tables(db_engine):
    """Create database tables for testing."""
    Base.metadata.create_all(bind=db_engine)
    yield
    Base.metadata.drop_all(bind=db_engine)


@pytest.fixture
def db_session(db_tables):
    """Create database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User"
    }
