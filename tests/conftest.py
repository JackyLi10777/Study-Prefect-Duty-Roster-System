"""
Shared test fixtures for the Sing Yin Study Prefect Duty Roster System.
"""

import pytest
import pandas as pd

@pytest.fixture
def sample_roster_rows():
    """Return the expected 6 roster rows."""
    from roster.config import get_roster_rows
    return get_roster_rows()

@pytest.fixture
def sample_days():
    """Return the 5 weekdays."""
    from roster.config import DAYS
    return DAYS

@pytest.fixture
def demo_students():
    """Return the full demo student DataFrame."""
    from roster.data.demo import get_demo_dataframe
    return get_demo_dataframe()

@pytest.fixture
def empty_roster_df():
    """Return an empty roster DataFrame with proper index/columns."""
    from roster.data.models import create_empty_roster_df
    return create_empty_roster_df()
