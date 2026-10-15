from pathlib import Path

from fastapi.testclient import TestClient

from depbridge_service.app import create_app
from depbridge_service.config import Settings
from depbridge_service.engine import EngineAdapter
from depbridge_service.ui import render_primary


ROOT = Path(__file__).resolve().parents[2]


def test_primary_shell_replaces_simulation_with_live_service():
    source = ROOT / "frontend" / "index.html"
    original = source.read_bytes()
    html = render_primary(source)
    assert 'id="live-submit"' in html and 'id="tab-verification"' in html
    assert '/static/css/styles.css' in html and '/service-ui/primary.js' in html
    for fake in ('js/data.js', 'js/app.js', '34 passed', 'd96a36f', 'Sandbox active', 'Demo simulation:', 'v1.4.2'):
        assert fake not in html
    assert 'No signed attestation is produced' in html
    assert source.read_bytes() == original


def test_primary_routes_assets_and_aliases(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", frontend_dir=ROOT / "frontend")
    with TestClient(create_app(settings, EngineAdapter("preview"))) as client:
        for url in ('/', '/static/index.html', '/static/start.html'):
            response = client.get(url)
            assert response.status_code == 200
            assert 'id="live-submit"' in response.text and 'js/data.js' not in response.text
        for path in ('/static/css/styles.css', '/service-ui/primary.js', '/service-ui/primary.css'):
            assert client.get(path).status_code == 200
        assert client.get('/reports/unknown').status_code == 404
        created = client.post('/api/analyses', json={'repository_url': 'https://github.com/rishrek/LinkWatch'})
        report = client.get('/reports/' + created.json()['analysis_id'])
        assert report.status_code == 200 and '/service-ui/primary.js' in report.text
