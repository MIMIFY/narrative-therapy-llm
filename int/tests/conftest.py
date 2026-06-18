import os

import pytest


os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")


def pytest_addoption(parser):
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run tests that call external LLM/RAG services",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: requires external LLM/RAG services")
    config.addinivalue_line("markers", "asyncio: run async test functions")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="need --runslow to run external integration tests")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def fake_session_data():
    return {
        "id": "test-session-001",
        "stage": "trust building",
        "stage_count": 1,
        "accomplish_goal": False,
        "turns": [
            {
                "round": 1,
                "client": "我最近压力很大，感觉什么都做不好。",
                "therapist": "听起来你承受了很多，能多说说是什么让你感到压力吗？",
                "stage": "trust building",
                "reflection_level": "探索问题事件",
                "rag_references": [],
                "user_cooperation": "",
                "timestamp": "2024-01-01T00:00:00Z",
            }
        ],
    }
