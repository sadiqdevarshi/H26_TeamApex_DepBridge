'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const list = (values, ordered=false) => values?.length ? `<${ordered?'ol':'ul'}>${values.map(v=>`<li>${esc(v)}</li>`).join('')}</${ordered?'ol':'ul'}>` : '<p class="live-muted">None recorded.</p>';
  const label = value => esc(String(value ?? 'Not available yet').replaceAll('_',' '));
  const pill = value => `<span class="status-pill status-pill-${['failed','differences_found'].includes(value)?'critical':['partial','inconclusive','blocked','not_run'].includes(value)?'warning':'neutral'}">${label(value)}</span>`;
  let analysisId = location.pathname.match(/^\/reports\/([^/]+)/)?.[1] || new URLSearchParams(location.search).get('analysis_id');
  let record = null, timer = null, busy = false, currentTab = 'findings', failures = 0;
  const active = value => ['queued','running'].includes(value);
  function error(message) {$('live-error').textContent=message; $('live-error').hidden=false;}
  function clearError() {$('live-error').hidden=true; $('live-error').textContent='';}
  async function api(path, options) {
    const response = await fetch(path, options);
    const body = await response.json();
    if (!response.ok) { const e = new Error(body.error?.message || `HTTP ${response.status}`); e.detail=body.error; e.status=response.status; throw e; }
    return body;
  }
  function download(url, title) {
    if (!url) return '';
    try { const u=new URL(url,location.origin); if(u.origin!==location.origin || !u.pathname.startsWith('/api/'))return ''; return `<a class="btn-base btn-primary" href="${esc(u.href)}">${esc(title)}</a>`; } catch {return '';}
  }
  function source(e) {
    try { const u=new URL(e.url); if(!['https:','http:'].includes(u.protocol))return ''; return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">Upstream source</a>`; } catch {return '';}
  }
  window.switchTab = tab => {
    currentTab=tab;
    for(const name of ['findings','codemod','verification','workspace','capsule']) {
      $('view-'+name).hidden=name!==tab;
      $('tab-'+name)?.classList.toggle('active',name===tab);
    }
  };
  window.handleReScan = () => $('live-submit').requestSubmit();
  function candidate(f,c) {
    const pending=record.verifications.some(v=>v.finding_id===f.finding_id && v.candidate_id===c.candidate_id && active(v.status));
    return `<article><h3>${esc(c.replacement_name || c.approach || 'Migration proposal')}</h3>${pill(c.recommendation_source)}<p>${esc(c.rationale)}</p><h3>Suggested migration steps</h3>${list(c.migration_steps,true)}<h3>Suggested checks · not execution results</h3>${list(c.suggested_checks)}<h3>Open concerns</h3>${list(c.limitations)}<button class="btn-base btn-primary" data-finding="${esc(f.finding_id)}" data-candidate="${esc(c.candidate_id)}" ${!c.verification_supported || pending || record.status!=='completed'?'disabled':''}>${pending?'Comparison running…':'Run comparison'}</button>${!c.verification_supported?`<p class="live-muted">${esc(c.unsupported_reason || 'not implemented: comparison unavailable')}</p>`:''}</article>`;
  }
  function usage(f) {return `<h3>${esc(f.dependency_name)}</h3>${f.usage.map(u=>`<p>${esc(u.path)}:${esc(u.start_line)} · ${esc(u.symbol)}</p><pre>${esc(u.excerpt)}</pre>`).join('')||'<p>No static usage matched; indirect usage may exist.</p>'}${list(f.limitations)}`;}
  function comparison(v) {
    return `<section class="card-surface live-card"><div class="live-row"><h2>Original versus candidate</h2>${pill(v.outcome || v.status)}</div><p class="live-muted">${esc(v.verification_id)} · ${label(v.stage)} · Python ${esc(v.environment?.python_version || 'Not available yet')} · ${esc(v.environment?.platform || '')}</p>${v.outcome==='supported'?'<p>Selected checks passed. Full application compatibility remains unverified.</p>':''}${v.error?`<p class="live-error">${esc(v.error.message)}</p>`:''}<div class="live-scroll"><table class="live-table"><thead><tr><th>Check</th><th>Original</th><th>Candidate</th><th>Observation</th></tr></thead><tbody>${v.checks.map(c=>`<tr><td>${esc(c.name)}<p class="live-muted">${esc(c.scope)}</p></td>${['original','candidate'].map(side=>`<td>${pill(c[side].status)}<details><summary>Logs and command</summary><pre>${esc(c[side].log_excerpt || 'No output recorded.')}</pre>${c[side].log_truncated?'<p>Excerpt truncated; full supplied logs are in the capsule.</p>':''}<pre>${esc(JSON.stringify(c[side].command))}</pre></details></td>`).join('')}<td>${esc(c.comparison_note)}</td></tr>`).join('')}</tbody></table></div>${list(v.limitations)}${download(v.patch_url,'Download patch')}</section>`;
  }
  function render(r) {
    record=r;
    const running=active(r.status)||r.verifications.some(v=>active(v.status));
    $('submit').disabled=active(r.status); $('rescanBtn').disabled=active(r.status);
    $('live-status').textContent=`${r.status} · ${r.stage} · ${r.analysis_id}`;
    $('live-revision').textContent=`${r.repository.name}@${r.repository.revision?.slice(0,8) || 'unresolved'}`;
    if(r.error) error(r.error.message);
    const s=r.summary, ai=r.ai;
    $('live-overview').innerHTML=`${r.data_mode==='mock'?'<p class="live-error">Design preview: sample data, not live results.</p>':''}<div class="live-row"><h1>${esc(r.repository.name)}</h1>${pill(r.outcome || r.status)}</div><p>Revision: <code>${esc(r.repository.revision || 'Not resolved yet')}</code></p><p class="live-muted">Python ${esc(r.environment.python_version || 'Not available yet')} · ${esc(r.environment.platform || '')} · Updated ${esc(r.updated_at)}</p><div class="live-stats">${[['Declared dependencies',s.dependencies_discovered],['Flagged dependencies',s.dependencies_flagged],['Migration proposals',s.migration_proposals],['Completed comparisons',s.completed_comparisons]].map(([k,v])=>`<div class="live-stat"><span>${k}</span><strong>${esc(v ?? '—')}</strong></div>`).join('')}</div><h2>Model contribution ${pill(ai.state)}</h2><p>${esc(ai.model_version || ai.model_name || 'No model recorded')} · ${esc(ai.access_method || 'Not available yet')}</p>${ai.error?`<p class="live-error">${esc(ai.error.message)}</p>`:''}<details><summary>Coverage, warnings and limitations</summary><p>Files scanned: ${esc(r.coverage.scanned_files ?? 'Unknown')} · Excluded: ${esc(r.coverage.excluded_files ?? 'Unknown')}</p>${list([...r.warnings,...r.coverage.limitations])}</details>`;
    $('live-findings').innerHTML=r.findings.map(f=>`<section class="card-surface live-card"><div class="live-row"><h2>${esc(f.dependency_name)} · ${esc(f.title)}</h2>${pill(f.evidence_strength)}</div><p>${esc(f.explanation)}</p><details><summary>Observed evidence and declarations</summary>${f.declarations.map(d=>`<p><code>${esc(d.path)} · ${esc(d.requirement)}</code></p>`).join('')}${f.evidence.map(e=>`<h3>${esc(e.title)}</h3><pre>${esc(e.observation)}</pre><p>${source(e)} ${esc(e.source_path || '')} · ${esc(e.retrieved_at || '')}</p>`).join('')||'<p>No evidence captured.</p>'}</details><details><summary>Observed usage locations</summary>${usage(f)}</details>${f.candidates.map(c=>candidate(f,c)).join('')}</section>`).join('')||`<section class="card-surface live-card">${r.status==='failed'?'Analysis failed; no clean result is claimed.':r.status==='completed'?'No findings within the recorded coverage.':'Waiting for observed findings…'}</section>`;
    $('live-proposals').innerHTML=r.findings.map(f=>`<h2>${esc(f.dependency_name)}</h2>${f.candidates.map(c=>candidate(f,c)).join('')}`).join('')||'<p>No proposals recorded.</p>';
    $('live-comparisons').innerHTML=r.verifications.map(comparison).join('')||'<section class="card-surface live-card">No comparison has been requested.</section>';
    $('live-usage').innerHTML=r.findings.map(usage).join('')||'<p>No usage records yet.</p>';
    $('live-downloads').innerHTML=download(r.downloads.capsule_url,'Download capsule')||`<p>${esc(r.downloads.unavailable_reason || 'Export unavailable.')}</p>`;
    $('live-downloads').innerHTML+=r.verifications.map(v=>download(v.patch_url,'Download patch')).join('');
    return running;
  }
  async function poll() {
    clearTimeout(timer); if(!analysisId)return; if(busy){timer=setTimeout(poll,250);return;} busy=true;
    const requestedId=analysisId;
    try { const r=await api('/api/analyses/'+encodeURIComponent(requestedId)); if(requestedId!==analysisId){timer=setTimeout(poll,0);return;} const again=render(r); failures=0; if(again)timer=setTimeout(poll,2000); }
    catch(e) {error(e.message); if(e.status!==404)timer=setTimeout(poll,Math.min(30000,2000*2**Math.min(++failures,4)));}
    finally {busy=false;}
  }
  $('live-submit').addEventListener('submit',async e=>{
    e.preventDefault(); if($('submit').disabled)return; clearError(); clearTimeout(timer); $('submit').disabled=true;
    try {const payload={repository_url:$('repository').value.trim()}; if($('ref').value.trim())payload.ref=$('ref').value.trim(); const r=await api('/api/analyses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); analysisId=r.analysis_id; history.pushState({},'',`/reports/${encodeURIComponent(analysisId)}`); await poll();}
    catch(e) {error(e.message); $('submit').disabled=false;}
  });
  document.querySelector('main').addEventListener('click',async e=>{
    const button=e.target.closest('button[data-candidate]'); if(!button || button.disabled)return; button.disabled=true; clearError();
    try { await api(`/api/analyses/${encodeURIComponent(analysisId)}/verifications`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({finding_id:button.dataset.finding,candidate_id:button.dataset.candidate})}); window.switchTab('verification'); await poll(); }
    catch(e) {if(e.detail?.verification_id){window.switchTab('verification'); await poll();}else{error(e.message);button.disabled=false;}}
  });
  window.addEventListener('popstate',()=>location.reload());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden && analysisId)poll();});
  document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return; const tabs=['findings','codemod','verification','workspace','capsule'];if(/^[1-5]$/.test(e.key))window.switchTab(tabs[Number(e.key)-1]);});
  window.switchTab(currentTab); if(analysisId)poll();
})();
