import pytest

@pytest.fixture
def mock_pr_data():
    return {
        "title": "Add authentication middleware",
        "description": "Implemented JWT based authentication for the API.",
        "files": [
            {"filename": "src/auth.py", "patch": "+ def verify_token(token):\n+   pass"},
            {"filename": "src/main.py", "patch": "+ from auth import verify_token"}
        ]
    }

@pytest.fixture
def mock_commits():
    return [
        {
            "author": {"login": "dev1"},
            "commit": {"author": {"name": "dev1", "date": "2023-10-01T12:00:00Z"}},
            "files": [{"filename": "src/auth.py"}],
            "sha": "abc1234"
        },
        {
            "author": {"login": "dev1"},
            "commit": {"author": {"name": "dev1", "date": "2023-10-05T12:00:00Z"}},
            "files": [{"filename": "src/utils.py"}],
            "sha": "def5678"
        },
        {
            "author": {"login": "dev2"},
            "commit": {"author": {"name": "dev2", "date": "2023-09-15T12:00:00Z"}},
            "files": [{"filename": "src/database.py"}],
            "sha": "ghi9012"
        }
    ]

@pytest.fixture
def mock_history_profiles():
    return {
        "dev1": {"Python", "JWT", "FastAPI"},
        "dev2": {"Python", "SQL", "Database Migration"}
    }
