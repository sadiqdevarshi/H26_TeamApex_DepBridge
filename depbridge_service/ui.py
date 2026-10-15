"""Connect the teammate's primary visual shell to live v1 service records.

The imported frontend source is preserved. Its design fixtures, simulated checks,
and synthetic signed exports are never loaded by the served live report.
"""
from pathlib import Path
import re


ASSETS = Path(__file__).parent / "static"


def primary_frontend(directory):
    return (directory / "css" / "styles.css").is_file() and (directory / "js" / "data.js").is_file()


def render_primary(index):
    source = index.read_text(encoding="utf-8")
    source = source.replace('href="css/styles.css"', 'href="/static/css/styles.css"')
    source = re.sub(r'<!-- TOP SIMULATION BANNER -->.*?(?=<!-- GLOBAL STICKY HEADER -->)',
                    '<div class="live-banner">Live service data · recommendations and executed checks remain separate.</div>\n', source, flags=re.S)
    source = source.replace("rishrek/LinkWatch@d96a", '<span id="live-revision">No analysis selected</span>')
    source = source.replace("Workspace Topology", "Usage locations").replace("Codemod Diff", "Migration proposals")
    source = re.sub(r'<main\b[^>]*>.*?</main>', MAIN, source, count=1, flags=re.S)
    source = re.sub(r'<aside\b[^>]*>.*?</aside>', '', source, flags=re.S)
    source = re.sub(r'<div\b[^>]*id="drawerOverlay"[^>]*>\s*</div>', '', source)
    source = re.sub(r'<footer\b[^>]*>.*?</footer>', '<footer class="live-footer">DepBridge · Team Apex · Selected checks do not establish full application compatibility. Capsules contain hashes, not cryptographic signatures.</footer>', source, flags=re.S)
    source = re.sub(r'<script\s+src="js/(?:data|app)\.js"\s*>\s*</script>', '', source)
    source = re.sub(r'<script>(.*?)</script>', lambda match: '<script>if(window.tailwind){' + match[1] + '}</script>'
                    if 'tailwind.config' in match[1] else match[0], source, flags=re.S)
    source = source.replace('</head>', '<link rel="stylesheet" href="/service-ui/primary.css"></head>')
    return source.replace('</body>', '<script src="/service-ui/primary.js" defer></script></body>')


MAIN = '''<main class="live-main">
<section class="card-surface live-card">
<form id="live-submit" class="live-form">
<label>Public GitHub repository<input id="repository" type="url" required value="https://github.com/rishrek/LinkWatch"></label>
<label class="live-ref">Ref (optional)<input id="ref" placeholder="Default branch"></label>
<button id="submit" class="btn-base btn-primary" type="submit">Analyze repository</button>
</form><p class="live-muted">Public LinkWatch prototype. Model credentials remain on the server.</p>
<p id="live-status" role="status" aria-live="polite">Ready to submit a repository. No sample results loaded.</p>
<p id="live-error" role="alert" hidden></p></section>
<section id="live-overview" class="card-surface live-card"><h1>Dependency analysis</h1><p>Submit a repository or open an existing report URL.</p></section>
<div id="view-findings"><div id="live-findings"></div></div>
<div id="view-codemod" hidden><section class="card-surface live-card"><h2>Migration proposals and available patches</h2><p class="live-muted">Proposals require review. A patch is available only after the engine actually produces one.</p><div id="live-proposals"></div></section></div>
<div id="view-verification" hidden><div id="live-comparisons"></div></div>
<div id="view-workspace" hidden><section class="card-surface live-card"><h2>Observed usage locations</h2><p>Static matching can miss dynamic and indirect imports. No complete topology claim is made.</p><div id="live-usage"></div></section></div>
<div id="view-capsule" hidden><section class="card-surface live-card"><h2>Dependency Exit Capsule</h2><div id="live-downloads"></div><p class="live-muted">Exports contain the actual recorded evidence, limitations, logs, commands and available patch. No signed attestation is produced.</p></section></div>
</main>'''
