import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adl.generate import generate  # noqa: E402
from adl.model import build_star_schema  # noqa: E402
from adl.quality import run_checks  # noqa: E402


@pytest.fixture(scope="session")
def generated():
    return generate()


@pytest.fixture(scope="session")
def quality(generated):
    return run_checks(generated.cases)


@pytest.fixture(scope="session")
def star(quality):
    return build_star_schema(quality.clean)
