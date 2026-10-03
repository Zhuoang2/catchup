from dataclasses import replace

import pytest

from catchup.config import Settings


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return replace(Settings.from_env(), data_dir=tmp_path)
