#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Expected object at {path}:{line_no}")
        rows.append(row)
    return rows


def compact_profile(row: dict[str, Any]) -> dict[str, Any]:
    by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in row.get("claims") or []:
        if isinstance(claim, dict) and claim.get("field"):
            by_field[str(claim["field"])].append(claim)
    evidence = {
        str(item["id"]): item
        for item in (row.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }

    def first(field: str) -> dict[str, Any] | None:
        return (by_field.get(field) or [None])[0]

    def view(claim: dict[str, Any] | None) -> dict[str, Any]:
        if not claim:
            return {"availability": "not_published", "value": None, "meta": {}}
        refs = [evidence[eid] for eid in claim.get("evidence_ids") or [] if eid in evidence]
        retrieved = sorted(str(item.get("retrieved_at")) for item in refs if item.get("retrieved_at"))
        return {
            "availability": claim.get("availability") or "unknown",
            "value": claim.get("value"),
            "currency": claim.get("currency"),
            "period": claim.get("reporting_period"),
            "platform": claim.get("platform"),
            "scope": claim.get("claim_scope"),
            "meta": {
                "source": refs[0].get("source_url") if refs else None,
                "sourceClass": refs[0].get("source_class") if refs else None,
                "retrievedAt": retrieved[-1] if retrieved else None,
                "effectiveAt": refs[0].get("effective_at") if refs else None,
                "hash": refs[0].get("content_sha256") if refs else None,
                "span": refs[0].get("claim_span") if refs else None,
            },
        }

    def available(claim: dict[str, Any]) -> bool:
        return claim.get("availability") == "available"

    financial = {
        key: view(first(f"financial.{key}"))
        for key in (
            "revenue",
            "operating_result",
            "profit_before_tax",
            "annual_result",
            "assets",
            "equity",
            "debt",
        )
    }

    used_ids: list[str] = []
    for claims in by_field.values():
        for claim in claims:
            for evidence_id in claim.get("evidence_ids") or []:
                if evidence_id in evidence and evidence_id not in used_ids:
                    used_ids.append(evidence_id)
    ledger = [
        {
            "id": evidence[eid].get("id"),
            "source": evidence[eid].get("source_url"),
            "sourceClass": evidence[eid].get("source_class"),
            "retrievedAt": evidence[eid].get("retrieved_at"),
            "effectiveAt": evidence[eid].get("effective_at"),
            "hash": evidence[eid].get("content_sha256"),
            "span": evidence[eid].get("claim_span"),
        }
        for eid in used_ids
    ]

    legal = view(first("legal_name"))
    return {
        "org": str(row.get("organisation_number") or ""),
        "name": legal.get("value") if legal.get("availability") == "available" else str(row.get("organisation_number") or "Unknown company"),
        "run": row.get("run") or {},
        "operations": row.get("operations") or {},
        "changes": row.get("changes") or [],
        "legal": legal,
        "form": view(first("legal_form")),
        "municipality": view(first("municipality")),
        "latestAccounts": view(first("latest_submitted_accounts")),
        "website": view(first("official_website")),
        "description": view(first("company_description")),
        "roles": view(first("roles")),
        "locations": view(first("locations")),
        "group": view(first("group_structure")),
        "workforce": view(first("external.workforce_snapshot")),
        "employeeCount": view(first("employee_count")),
        "financial": financial,
        "contacts": [view(claim) for claim in by_field.get("external.contact_email") or [] if available(claim)],
        "handles": [view(claim) for claim in by_field.get("external.profile_handle") or [] if available(claim)],
        "evidence": ledger,
    }


def build_html(rows: list[dict[str, Any]], title: str = "Signalpost evidence workspace") -> str:
    payload = json.dumps(
        [compact_profile(row) for row in rows],
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    title = html.escape(title)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>
:root{{--paper:#f4f0e7;--card:#fffdf8;--ink:#181715;--muted:#706b62;--line:#d8d0c3;--accent:#762838;--good:#276044;--warn:#916114;--bad:#8d3535}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 system-ui,sans-serif}}a{{color:var(--accent);overflow-wrap:anywhere}}button,input{{font:inherit}}.mast{{background:var(--card);border-bottom:1px solid var(--line);padding:15px 22px;display:flex;justify-content:space-between;gap:14px;position:sticky;top:0;z-index:5}}.brand,h1,h2,h3{{font-family:Georgia,serif}}.brand{{font-weight:700;font-size:18px}}.brand i{{display:inline-block;width:10px;height:10px;background:var(--accent);transform:rotate(45deg);margin-right:9px}}.meta,.muted,small{{color:var(--muted)}}.hero{{max-width:1480px;margin:auto;padding:28px 22px 18px}}.eyebrow,.label{{font-size:10px;text-transform:uppercase;letter-spacing:.11em;font-weight:800;color:var(--accent)}}h1{{font-size:clamp(34px,5vw,60px);line-height:1;margin:7px 0 12px}}.lede{{max-width:900px;font-size:16px;color:var(--muted)}}.guard{{max-width:950px;margin-top:13px;padding:9px 12px;border-left:3px solid var(--accent);background:#f8edf0;color:#63323b}}.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:18px}}.stat,.panel,.box{{background:var(--card);border:1px solid var(--line)}}.stat{{padding:11px}}.stat strong{{display:block;font:600 23px Georgia,serif}}.shell{{max-width:1480px;margin:auto;padding:0 22px 44px;display:grid;grid-template-columns:275px minmax(0,1fr) 290px;gap:14px;align-items:start}}.panel,.shell>*{{min-width:0;max-width:100%}}.index,.side{{position:sticky;top:65px}}.head,.search,.profile,.side{{padding:14px}}.head{{display:flex;justify-content:space-between;align-items:end}}.head strong{{font:600 22px Georgia,serif}}.search{{border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.search input{{width:100%;padding:8px;border:1px solid var(--line)}}.list{{max-height:calc(100vh - 185px);overflow:auto}}.row{{display:block;width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;text-align:left;padding:10px 13px;cursor:pointer}}.row.active,.row:hover{{background:#eee7dc}}.row strong,.row small{{display:block}}.profile-head{{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:14px}}h2{{font-size:34px;line-height:1.05;margin:4px 0}}h3{{font-size:20px;margin:4px 0 9px}}.chips{{display:flex;gap:5px;flex-wrap:wrap}}.chip{{border:1px solid var(--line);border-radius:999px;padding:2px 6px;font-size:10px}}.chip.good{{color:var(--good)}}.chip.warn{{color:var(--warn)}}.chip.bad{{color:var(--bad)}}.brief{{margin:15px 0;padding:12px;background:#fbf8f1;border:1px solid var(--line)}}.brief p{{margin:4px 0}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}}.box{{padding:10px;min-width:0}}.box span{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}.box strong{{display:block;margin-top:3px;overflow-wrap:anywhere}}section{{border-top:1px solid var(--line);padding:16px 0}}table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:12px}}th,td{{border-bottom:1px solid var(--line);padding:7px;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{width:28%;color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}}.item{{border:1px solid var(--line);padding:9px;min-width:0}}.item strong,.item small{{display:block}}.unknown{{padding:8px 10px;background:#faf4e8;border-left:3px solid var(--warn);margin:5px 0}}details.source{{margin-top:7px;font-size:11px;color:var(--muted)}}details.source summary{{cursor:pointer;font-weight:700;color:var(--ink)}}code{{word-break:break-all;font-size:9px}}.evidence{{border:1px solid var(--line);padding:8px;margin:6px 0;overflow-wrap:anywhere}}.side{{background:var(--ink);color:white}}.side .eyebrow{{color:#deb2bb}}.actions{{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin:10px 0}}.actions button{{border:1px solid #5b5650;background:transparent;color:white;padding:7px;text-align:left}}.actions button.active,.actions button:hover{{background:var(--accent)}}.answer{{border-top:1px solid #4d4842;padding-top:10px}}.answer a{{color:#f2c9d0}}.ops{{border-top:1px solid #4d4842;margin-top:12px;padding-top:10px;font-size:11px;color:#c9c2ba}}@media(max-width:1100px){{.shell{{grid-template-columns:250px 1fr}}.side{{grid-column:2;position:static}}}}@media(max-width:820px){{.shell{{grid-template-columns:1fr}}.index,.side{{position:static}}.side{{grid-column:1}}.stats{{grid-template-columns:repeat(2,1fr)}}.list{{max-height:330px}}}}@media(max-width:520px){{.mast,.hero,.shell{{padding-left:13px;padding-right:13px}}.mast{{flex-wrap:wrap}}.meta{{max-width:100%;overflow-wrap:anywhere}}.stats,.grid,.cards{{grid-template-columns:1fr}}.profile{{padding:13px}}h2{{font-size:28px}}}}
</style></head><body><header class="mast"><div class="brand"><i></i>Signalpost evidence workspace</div><div class="meta" id="runmeta"></div></header><main><div class="hero"><div class="eyebrow">Final-output contract view</div><h1>Company intelligence you can trace back to evidence.</h1><p class="lede">Official identity and filings, workforce, verified first-party web/contact signals, explicit unknowns, freshness and change history.</p><div class="guard"><strong>Claim boundary:</strong> no reviews, buzz, sentiment, hiring activity, platform metrics or missing values are inferred. “Not published” means the qualified pipeline did not publish that claim in this run; it does not mean zero.</div><div class="stats" id="stats"></div></div><div class="shell"><aside class="panel index"><div class="head"><div><div class="eyebrow">Release corpus</div><strong>Companies</strong></div><span id="total"></span></div><div class="search"><input id="q" type="search" placeholder="Search name, org number, municipality"><small id="count"></small></div><div class="list" id="list"></div></aside><article class="panel profile" id="profile"></article><aside class="panel side"><div class="eyebrow">Evidence brief</div><h3>Ask the selected record.</h3><p>Deterministic synthesis from published claims only.</p><div class="actions" id="actions"><button data-mode="brief" class="active">Brief</button><button data-mode="financials">Financials</button><button data-mode="workforce">Workforce</button><button data-mode="leadership">Leadership</button><button data-mode="locations">Locations</button><button data-mode="external">External footprint</button><button data-mode="changes">Changes</button><button data-mode="evidence">Evidence</button></div><div class="answer" id="answer"></div><div class="ops" id="ops"></div></aside></div></main>
<script>const DATA={payload},$=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])),norm=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(),money=(v,c)=>v==null?'Not published':new Intl.NumberFormat('en-US',{{maximumFractionDigits:0}}).format(v)+' '+(c||'');let selected=null,mode='brief';const avail=c=>c?.availability==='available',state=c=>(c?.availability||'not_published').replaceAll('_',' '),name=x=>x.name||x.org;
function source(c,label='Inspect evidence'){{const m=c?.meta||{{}};return m.source?`<details class="source"><summary>${{esc(label)}}</summary><a href="${{esc(m.source)}}" target="_blank" rel="noreferrer">${{esc(m.source)}}</a><div>${{esc(m.sourceClass||'source')}} · retrieved ${{esc(m.retrievedAt||'not reported')}}${{m.effectiveAt?` · effective ${{esc(m.effectiveAt)}}`:''}}</div>${{m.span?`<div>${{esc(m.span)}}</div>`:''}}${{m.hash?`<code>${{esc(m.hash)}}</code>`:''}}</details>`:''}}function chip(label,c){{let s=state(c),cl=s==='available'?'good':/failed|blocked/.test(s)?'bad':'warn';return `<span class="chip ${{cl}}">${{esc(label)}}: ${{esc(s)}}</span>`}}function period(x){{for(const c of Object.values(x.financial))if(c.period)return c.period;return null}}function periodText(p){{return p?`${{p.fraDato||'?'}} → ${{p.tilDato||'?'}}`:'Not published'}}function workforce(x){{if(!avail(x.workforce))return 'No qualified workforce snapshot published';const v=x.workforce.value||{{}},m=v.measure==='full_time_equivalents'?'FTE':v.measure==='employees'?'employees':v.measure||'workforce',y=x.workforce.meta?.effectiveAt?` for ${{x.workforce.meta.effectiveAt}}`:'';return `${{v.value??'Not published'}} ${{m}}${{y}}`}}function refs(cs){{const us=[];for(const c of cs){{let u=c?.meta?.source;if(u&&!us.includes(u))us.push(u)}}return us.length?`<small>Sources:<br>${{us.map(u=>`<a href="${{esc(u)}}" target="_blank" rel="noreferrer">${{esc(u)}}</a>`).join('<br>')}}</small>`:''}}
function renderStats(){{let w=DATA.filter(x=>avail(x.workforce)).length,s=DATA.filter(x=>avail(x.website)).length,e=DATA.filter(x=>x.contacts.length).length,h=DATA.filter(x=>x.handles.length).length;$('#total').textContent=DATA.length;$('#stats').innerHTML=[[DATA.length,'terminal company outputs'],[w,'workforce observations'],[s,'verified websites'],[e,'companies with contact email'],[h,'companies with declared social handles']].map(([v,l])=>`<div class="stat"><strong>${{v}}</strong><small>${{l}}</small></div>`).join('');let runs=[...new Set(DATA.map(x=>x.run?.run_id).filter(Boolean))];$('#runmeta').textContent=`${{DATA.length}} companies · ${{runs.length}} evaluator-shaped run${{runs.length===1?'':'s'}} · final contract`}}function filtered(){{let q=norm($('#q').value);return DATA.filter(x=>!q||norm([name(x),x.org,x.municipality.value].join(' ')).includes(q)).sort((a,b)=>name(a).localeCompare(name(b),'nb'))}}function renderList(){{let rows=filtered();$('#count').textContent=`${{rows.length}} matching`;$('#list').innerHTML=rows.map(x=>`<button class="row ${{selected?.org===x.org?'active':''}}" data-org="${{esc(x.org)}}"><strong>${{esc(name(x))}}</strong><small>${{esc(x.org)}} · ${{esc(x.municipality.value||'municipality not published')}}</small></button>`).join('');$('#list').querySelectorAll('.row').forEach(b=>b.onclick=()=>{{selected=DATA.find(x=>x.org===b.dataset.org);mode='brief';renderList();renderProfile();renderAnswer()}});if(!selected&&rows.length){{selected=rows[0];renderList();renderProfile();renderAnswer()}}}}
function unknowns(x){{let a=[];if(!avail(x.website))a.push(`Website: ${{state(x.website)}}.`);if(!x.contacts.length)a.push('Contact email: no qualifying same-domain email was published from a verified company site.');if(!x.handles.length)a.push('Social profiles: no qualifying first-party-declared handle was published.');if(!avail(x.workforce))a.push('Workforce: no qualified live-registry or annual-report observation was published.');if(!avail(x.financial.revenue))a.push('Revenue: no normalized claim was published; missing is not zero.');if(!avail(x.group))a.push(`Group structure: ${{state(x.group)}}.`);return a}}function brief(x){{let ext=[];if(x.contacts.length)ext.push(`${{x.contacts.length}} contact email${{x.contacts.length===1?'':'s'}}`);if(x.handles.length)ext.push(`${{x.handles.length}} declared social handle${{x.handles.length===1?'':'s'}}`);return `<div class="brief"><div class="label">Company brief</div><p><strong>${{esc(name(x))}}</strong> (${{esc(x.org)}}) is published as ${{esc(x.form.value||'legal form not published')}} in ${{esc(x.municipality.value||'municipality not published')}}.</p><p>Latest accounts: <strong>${{esc(x.latestAccounts.value||'not published')}}</strong>; normalized period: <strong>${{esc(periodText(period(x)))}}</strong>.</p><p>Workforce: <strong>${{esc(workforce(x))}}</strong>. ${{avail(x.website)?`Verified website: <a href="${{esc(x.website.value)}}" target="_blank">${{esc(x.website.value)}}</a>.`:'No verified website was published.'}}</p><p>External first-party signals: <strong>${{esc(ext.length?ext.join(' · '):'none published by the qualified extractors')}}</strong>.</p></div>`}}
function renderProfile(){{let x=selected;if(!x)return;let roles=(x.roles.value?.roles||[]).filter(r=>!r.inactive),locs=x.locations.value?.locations||[],u=unknowns(x);$('#profile').innerHTML=`<div class="profile-head"><div><div class="eyebrow">Final output contract</div><h2>${{esc(name(x))}}</h2><div>${{esc(x.org)}} · ${{esc(x.form.value||'form not published')}}</div></div><div class="chips">${{chip('website',x.website)}}${{chip('workforce',x.workforce)}}${{chip('roles',x.roles)}}${{chip('group',x.group)}}</div></div>${{brief(x)}}${{avail(x.description)?`<p>${{esc(x.description.value)}}</p>`:''}}<div class="grid"><div class="box"><span>Municipality</span><strong>${{esc(x.municipality.value||'Not published')}}</strong></div><div class="box"><span>Latest submitted accounts</span><strong>${{esc(x.latestAccounts.value||'Not published')}}</strong></div><div class="box"><span>Workforce</span><strong>${{esc(workforce(x))}}</strong></div><div class="box"><span>Financial period</span><strong>${{esc(periodText(period(x)))}}</strong></div><div class="box"><span>Verified website</span><strong>${{avail(x.website)?`<a href="${{esc(x.website.value)}}" target="_blank">${{esc(x.website.value)}}</a>`:'Not published'}}</strong></div><div class="box"><span>Evidence records</span><strong>${{x.evidence.length}}</strong></div></div><section><div class="label">Official financials</div><h3>Period-aware filing facts</h3><table>${{[['Revenue','revenue'],['Operating result','operating_result'],['Profit before tax','profit_before_tax'],['Annual result','annual_result'],['Assets','assets'],['Equity','equity'],['Debt','debt']].map(([l,k])=>{{let c=x.financial[k];return `<tr><th>${{l}}</th><td><strong>${{money(c.value,c.currency)}}</strong><br><small>${{esc(periodText(c.period))}} · ${{esc(state(c))}}</small>${{source(c)}}</td></tr>`}}).join('')}}</table></section><section><div class="label">Workforce</div><h3>${{esc(workforce(x))}}</h3><p>${{esc(x.workforce.scope||'Published workforce evidence is source-bounded; no trend is inferred.')}}</p>${{source(x.workforce)}}${{avail(x.employeeCount)?`<div class="item"><strong>Live registry employee count: ${{esc(x.employeeCount.value)}}</strong>${{source(x.employeeCount)}}</div>`:''}}</section><section><div class="label">External footprint</div><h3>Verified first-party signals only</h3><div class="cards"><div class="item"><strong>Website</strong><small>${{avail(x.website)?`<a href="${{esc(x.website.value)}}" target="_blank">${{esc(x.website.value)}}</a>`:esc(state(x.website))}}</small>${{source(x.website)}}</div><div class="item"><strong>Contact email</strong><small>${{x.contacts.length?x.contacts.map(c=>esc(c.value)).join('<br>'):'No qualifying email published'}}</small>${{x.contacts.map(c=>source(c,'Email evidence')).join('')}}</div>${{x.handles.length?x.handles.map(c=>`<div class="item"><strong>${{esc(c.platform||'profile')}}</strong><small><a href="${{esc(c.value)}}" target="_blank">${{esc(c.value)}}</a></small>${{source(c,'Declaration evidence')}}</div>`).join(''):'<div class="item"><strong>Social profiles</strong><small>No qualifying first-party-declared handle published.</small></div>'}}</div><p class="muted">A social claim means only that the exact verified company page declared the URL. Platform activity, followers, sentiment and current account ownership are not inferred.</p></section><section><div class="label">Leadership</div><h3>${{roles.length}} current public role records</h3><div class="cards">${{roles.length?roles.slice(0,20).map(r=>`<div class="item"><strong>${{esc(Array.isArray(r.name)?r.name.join(', '):r.name||r.organisation_number||'Unnamed holder')}}</strong><small>${{esc(r.role||r.group||r.role_code||'role not published')}}</small></div>`).join(''):'<p class="muted">No role record published.</p>'}}</div>${{source(x.roles)}}</section><section><div class="label">Registered locations</div><h3>${{locs.length}} subunit record${{locs.length===1?'':'s'}}</h3><div class="cards">${{locs.length?locs.slice(0,20).map(l=>`<div class="item"><strong>${{esc(l.name||l.organisation_number||'Unnamed subunit')}}</strong><small>${{esc(l.address?.adresse?.join(', ')||'address not published')}} · ${{esc(l.address?.poststed||l.address?.kommune||'place not published')}}</small></div>`).join(''):'<p class="muted">No registered subunit record published.</p>'}}</div>${{source(x.locations)}}</section><section><div class="label">Unknown / unavailable</div><h3>What this run does not establish</h3>${{u.length?u.map(t=>`<div class="unknown">${{esc(t)}}</div>`).join(''):'<div class="unknown">No key-field gap from this display set. This does not imply completeness outside the published claim families.</div>'}}</section><section><div class="label">Change history</div><h3>${{x.changes.length}} recorded change${{x.changes.length===1?'':'s'}}</h3>${{x.changes.length?`<table>${{x.changes.map(c=>`<tr><th>${{esc(c.field||'field')}}</th><td>${{esc(JSON.stringify(c.old_value))}} → ${{esc(JSON.stringify(c.new_value))}}</td></tr>`).join('')}}</table>`:'<p class="muted">No change event is attached to this output.</p>'}}</section><section><div class="label">Evidence ledger</div><h3>${{x.evidence.length}} linked evidence records</h3>${{x.evidence.map(e=>`<div class="evidence"><strong>${{esc(e.sourceClass||'source')}}</strong> · <a href="${{esc(e.source||'#')}}" target="_blank">source ↗</a><div>${{esc(e.span||'No claim span published')}}</div><small>Retrieved ${{esc(e.retrievedAt||'not published')}}${{e.effectiveAt?` · effective ${{esc(e.effectiveAt)}}`:''}}</small>${{e.hash?`<div><code>${{esc(e.hash)}}</code></div>`:''}}</div>`).join('')}}</section>`}}
function renderAnswer(){{let x=selected;if(!x)return;let f=x.financial,out='';if(mode==='brief')out=`<p><strong>${{esc(name(x))}}</strong> · ${{esc(x.form.value||'form not published')}} · ${{esc(x.municipality.value||'municipality not published')}}.</p><p>Latest accounts: <strong>${{esc(x.latestAccounts.value||'not published')}}</strong>. Workforce: <strong>${{esc(workforce(x))}}</strong>.</p><p>${{avail(x.website)?'Verified first-party website is published.':'No verified website is published.'}} ${{x.contacts.length?`${{x.contacts.length}} qualifying contact email(s).`:'No qualifying contact email published.'}}</p>${{refs([x.legal,x.form,x.municipality,x.latestAccounts,x.workforce,x.website])}}`;if(mode==='financials')out=`<p>Reporting period: <strong>${{esc(periodText(period(x)))}}</strong>.</p><p>Revenue: <strong>${{money(f.revenue.value,f.revenue.currency)}}</strong><br>Operating result: <strong>${{money(f.operating_result.value,f.operating_result.currency)}}</strong><br>Annual result: <strong>${{money(f.annual_result.value,f.annual_result.currency)}}</strong><br>Debt: <strong>${{money(f.debt.value,f.debt.currency)}}</strong></p>${{refs(Object.values(f))}}`;if(mode==='workforce')out=`<p><strong>${{esc(workforce(x))}}</strong></p><p>${{esc(x.workforce.scope||'No qualified workforce claim is published.')}}</p>${{refs([x.workforce,x.employeeCount])}}`;if(mode==='leadership'){{let rs=(x.roles.value?.roles||[]).filter(r=>!r.inactive);out=rs.length?`<p>${{rs.slice(0,6).map(r=>`<strong>${{esc(Array.isArray(r.name)?r.name.join(', '):r.name||'holder')}}</strong> — ${{esc(r.role||r.group||'role')}}`).join('<br>')}}</p>${{refs([x.roles])}}`:'<p>No public role record is published.</p>'}}if(mode==='locations'){{let ls=x.locations.value?.locations||[];out=ls.length?`<p>${{ls.slice(0,6).map(l=>`<strong>${{esc(l.name||'subunit')}}</strong> — ${{esc(l.address?.poststed||l.address?.kommune||'place not published')}}`).join('<br>')}}</p>${{refs([x.locations])}}`:'<p>No registered subunit record is published.</p>'}}if(mode==='external')out=`<p>${{avail(x.website)?`Website: <a href="${{esc(x.website.value)}}" target="_blank">${{esc(x.website.value)}}</a>`:`Website: ${{esc(state(x.website))}}`}}</p><p>${{x.contacts.length?`Contact: ${{x.contacts.map(c=>esc(c.value)).join(', ')}}`:'No qualifying contact email published.'}}</p><p>${{x.handles.length?x.handles.map(c=>`<strong>${{esc(c.platform)}}</strong>: <a href="${{esc(c.value)}}" target="_blank">declared profile ↗</a>`).join('<br>'):'No qualifying first-party-declared social handle published.'}}</p>${{refs([x.website,...x.contacts,...x.handles])}}`;if(mode==='changes')out=x.changes.length?`<p>${{x.changes.map(c=>`<strong>${{esc(c.field||'field')}}</strong>: ${{esc(JSON.stringify(c.old_value))}} → ${{esc(JSON.stringify(c.new_value))}}`).join('<br>')}}</p>`:'<p>No change event is attached to this output.</p>';if(mode==='evidence')out=`<p><strong>${{x.evidence.length}} evidence records</strong> link to published claims.</p><p>Latest retrieval: <strong>${{esc(x.evidence.map(e=>e.retrievedAt).filter(Boolean).sort().at(-1)||'not published')}}</strong>.</p><p>Use the Evidence ledger for source URLs, spans, freshness and hashes.</p>`;$('#answer').innerHTML=out;$('#actions').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));$('#ops').innerHTML=`Run: ${{esc(x.run?.run_id||'not published')}}<br>Terminal: ${{esc(x.run?.terminal_status||'not published')}}<br>Requests charged: ${{esc(x.operations?.requests??'not published')}}<br>Runtime: ${{x.operations?.runtime_ms!=null?esc((x.operations.runtime_ms/1000).toFixed(2)+'s'):'not published'}}<br>Third-party cost: ${{x.operations?.third_party_cost_usd!=null?'$'+esc(x.operations.third_party_cost_usd):'not published'}}`}}$('#q').addEventListener('input',()=>{{selected=null;renderList()}});$('#actions').querySelectorAll('button').forEach(b=>b.onclick=()=>{{mode=b.dataset.mode;renderAnswer()}});renderStats();renderList();</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the release-facing Signalpost workspace from final output-contract JSONL."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--title", default="Signalpost evidence workspace")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit cannot be negative")
    rows = read_jsonl(Path(args.input))
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("No output rows found")

    try:
        from norway_company_agent.output_contract import validate_contract_object
    except ImportError:
        validate_contract_object = None
    if validate_contract_object:
        failures = [
            (row.get("organisation_number"), validate_contract_object(row))
            for row in rows
        ]
        failures = [(org, errors) for org, errors in failures if errors]
        if failures:
            raise SystemExit(
                f"Input contains contract validation failures: {json.dumps(failures[:5], ensure_ascii=False)}"
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(rows, args.title), encoding="utf-8")
    print(json.dumps({"profiles": len(rows), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
