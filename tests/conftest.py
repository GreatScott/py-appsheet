import os
import pytest
from dotenv import load_dotenv
from py_appsheet import AppSheetClient


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test requiring real AppSheet credentials"
    )


@pytest.fixture(scope="session")
def client():
    load_dotenv()
    app_id = os.getenv("APP_ID")
    access_key = os.getenv("ACCESS_KEY")
    if not app_id or not access_key:
        pytest.skip("APP_ID and ACCESS_KEY not found in .env — skipping integration tests")
    return AppSheetClient(app_id=app_id, api_key=access_key)
