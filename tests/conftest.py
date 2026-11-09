"""Keep the tests' git subprocesses inside their temporary repositories.

When pytest runs from a git hook (the pre-commit gate), git exports GIT_INDEX_FILE, GIT_DIR and friends
into the hook's environment. A test that then runs `git add` in a tmp_path repository inherits them and
writes that repository's entries into adrcheck's own index, pointing at blobs the real object store does
not hold; the commit then fails with "invalid object ... Error building trees". Scrub them once per
session. adrcheck itself keeps the variables: `adrcheck check --staged` is meant to run inside a hook.
"""

import os

import pytest

_HOOK_VARS = (
    "GIT_INDEX_FILE",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True, scope="session")
def _git_env_is_the_test_repos_own():
    for var in _HOOK_VARS:
        os.environ.pop(var, None)
    yield


def test_hook_environment_is_scrubbed():
    assert not any(var in os.environ for var in _HOOK_VARS)
