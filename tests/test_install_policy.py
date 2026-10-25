"""Guard the supported installer's dependency-integrity contract."""

from pathlib import Path


def test_installer_enforces_hashed_lockfiles_without_unpinned_pip_upgrades():
    script = (Path(__file__).resolve().parents[1] / 'install.sh').read_text(encoding='utf-8')
    assert '.venv/bin/python -m pip install --require-hashes -r "$dependency_file"' in script
    assert 'pip install --upgrade pip' not in script
