from pathlib import Path
import pytest
from depbridge_engine.engine import github_url, declarations, usages, add_ai
from depbridge_engine.engine import _generate_with_retry
from types import SimpleNamespace
import json
import sys
from depbridge_engine.verification import _execute


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


def test_retry_recovers_from_temporary_provider_failure(monkeypatch):
    monkeypatch.setattr('depbridge_engine.engine.time.sleep', lambda _: None)
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            error = RuntimeError('temporary')
            error.code = 503
            raise error
        return SimpleNamespace(text='ok')
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    assert _generate_with_retry(client, 'gemma-4-test', 'test').text == 'ok'
    assert len(calls) == 2


def test_authentication_error_is_not_retried():
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        error = RuntimeError('authentication failure')
        error.code = 403
        raise error
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    with pytest.raises(RuntimeError):
        _generate_with_retry(client, 'gemma-4-test', 'test')
    assert len(calls) == 1


def test_gemma_single_string_limitations_are_preserved(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'unit-test-placeholder')
    monkeypatch.setenv('GEMMA_MODEL', 'gemma-4-26b-a4b-it')
    proposal = {'finding_id': 'example', 'rationale': 'Review observed usage.',
                'migration_steps': ['Change the import.'], 'suggested_checks': ['Run the unchanged checks.'],
                'limitations': 'Full-suite compatibility remains unverified.'}
    response = SimpleNamespace(text='```json\n' + json.dumps({'proposals': [proposal]}) + '\n```')
    monkeypatch.setattr('depbridge_engine.engine._generate_with_retry', lambda *args: response)
    fake_client = lambda **kwargs: SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'google.genai', SimpleNamespace(Client=fake_client))
    monkeypatch.setitem(sys.modules, 'google', SimpleNamespace(genai=SimpleNamespace(Client=fake_client)))
    findings = [{'finding_id': 'example', 'dependency_name': 'appdirs', 'evidence': [], 'usage': [],
                 'candidates': [{'replacement_name': 'platformdirs', 'verification_supported': False}]}]
    result = add_ai(findings)
    assert result['state'] == 'completed'
    candidate = findings[0]['candidates'][0]
    assert candidate['limitations'] == ['Full-suite compatibility remains unverified.']
    assert candidate['recommendation_source'] == 'gemma4'
    assert candidate['verification_supported'] is False


def test_execution_records_actual_arguments(tmp_path):
    command = [sys.executable, '-c', 'print("observed execution")']
    result = _execute(command, tmp_path)
    assert result['status'] == 'passed'
    assert result['command'] == command
    assert 'observed execution' in result['full_log']
