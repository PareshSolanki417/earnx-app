import os
import sys
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is on sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.admin import AdminUser
from app.models.wallet import Wallet
from app.utils.seed import seed_database
from app.security.deps import hash_password, create_access_token

# In-memory SQLite for fast, isolated automated testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as session:
        seed_database(session)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session) -> User:
    user = User(
        telegram_id=88888888,
        username="pytest_user",
        first_name="Test",
        last_name="User",
        referral_code="EARNTEST",
        status="ACTIVE",
        risk_level="LOW",
    )
    db_session.add(user)
    db_session.flush()

    wallet = Wallet(
        user_id=user.id,
        available_coins=Decimal("200.0000"),
        pending_coins=Decimal("0.0000"),
        lifetime_earned=Decimal("200.0000"),
        lifetime_withdrawn=Decimal("0.0000"),
    )
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_auth_headers(test_user) -> dict:
    token = create_access_token({"sub": str(test_user.id), "role": "user", "telegram_id": test_user.telegram_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(db_session) -> dict:
    admin = db_session.query(AdminUser).filter(AdminUser.username == "admin").first()
    if not admin:
        admin = AdminUser(
            username="admin",
            email="admin@earnx.app",
            hashed_password=hash_password("AdminEarnX2026!"),
            role="SUPERADMIN",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    token = create_access_token({"sub": str(admin.id), "role": "admin", "username": admin.username})
    return {"Authorization": f"Bearer {token}"}
