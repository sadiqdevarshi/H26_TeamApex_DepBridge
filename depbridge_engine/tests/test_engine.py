from pathlib import Path
import pytest
from depbridge_engine.engine import github_url, declarations, usages, add_ai


def test_url_rejects_credentials_options_and_other_hosts():
    assert github_url("https://github.com/rishrek/LinkWatch.git") == "https://github.com/rishrek/LinkWatch"
    for value in ("https://token@github.com/a/b", "https://example.org/a/b", "--upload-pack=evil", "https://github.com/a/b?token=x"):
        with pytest.raises(ValueError):
            github_url(value)


def test_manifest_and_aliased_import(tmp_path):
    (tmp_path / "requirements.txt").write_text("appdirs==1.4.4\npydantic==1.10.13\n")
    (tmp_path / "cache.py").write_text("from appdirs import user_cache_dir as cache\n")
    records, errors = declarations(tmp_path)
    assert not errors
    assert {r['name'] for r in records} == {'appdirs', 'pydantic'}
    usage, scanned, excluded = usages(tmp_path, {'appdirs'})
    assert scanned == 1
    assert usage['appdirs'][0]['start_line'] == 1


def test_missing_key_does_not_claim_ai_execution(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    assert add_ai([])['state'] == 'not_run'
