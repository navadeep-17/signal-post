#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402


AREA_ORDER = (
    ("company_record", "Company record"),
    ("financials", "Financials"),
    ("people_and_locations", "People & locations"),
    ("company_website", "Company website"),
    ("hiring_and_public_activity", "Hiring & public activity"),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Expected object at {path}:{line_no}")
            rows.append(row)
    return rows


def ensure_canonical(row: dict[str, Any]) -> dict[str, Any]:
    item = row if isinstance(row.get("canonical_profile"), dict) else project_canonical_profile(row)
    source_errors = validate_contract_object(item)
    canonical_errors = validate_canonical_projection(item)
    if source_errors or canonical_errors:
        raise ValueError(
            f"{item.get('organisation_number')}: contract={source_errors}; canonical={canonical_errors}"
        )
    return item


def _evidence_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in (row.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }


def _fact_view(fact: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    refs = [evidence[eid] for eid in fact.get("evidence_ids") or [] if eid in evidence]
    return {
        "type": fact.get("type"),
        "field": fact.get("canonical_field"),
        "sourceField": fact.get("source_field"),
        "value": fact.get("value"),
        "availability": fact.get("availability"),
        "confidence": fact.get("confidence"),
        "currency": fact.get("currency"),
        "period": fact.get("reporting_period"),
        "platform": fact.get("platform"),
        "scope": fact.get("claim_scope"),
        "evidence": [
            {
                "id": item.get("id"),
                "url": item.get("source_url"),
                "sourceClass": item.get("source_class"),
                "retrievedAt": item.get("retrieved_at"),
                "effectiveAt": item.get("effective_at") or item.get("as_of"),
                "span": item.get("claim_span"),
                "hash": item.get("content_sha256"),
            }
            for item in refs
        ],
    }


def compact_company(row: dict[str, Any]) -> dict[str, Any]:
    item = ensure_canonical(row)
    profile = item["canonical_profile"]
    evidence = _evidence_map(item)

    def views(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [_fact_view(fact, evidence) for fact in rows]

    company_record = views(profile.get("company_record") or [])
    name_fact = next(
        (fact for fact in company_record if fact.get("type") == "company_name" and fact.get("availability") == "available"),
        None,
    )
    municipality_fact = next(
        (fact for fact in company_record if fact.get("type") == "municipality" and fact.get("availability") == "available"),
        None,
    )
    jobs = views(profile.get("jobs") or [])
    activity = views(profile.get("public_activity") or [])
    return {
        "org": str(item.get("organisation_number") or ""),
        "name": (name_fact or {}).get("value") or str(item.get("organisation_number") or "Unknown company"),
        "municipality": (municipality_fact or {}).get("value"),
        "run": item.get("run") or {},
        "operations": item.get("operations") or {},
        "changes": item.get("changes") or [],
        "areas": {
            "company_record": company_record,
            "financials": views(profile.get("financials") or []),
            "people_and_locations": views((profile.get("people") or []) + (profile.get("locations") or [])),
            "company_website": views(profile.get("company_website") or []),
            "hiring_and_public_activity": jobs + activity,
        },
        "areaAvailability": profile.get("data_areas") or {},
        "counts": {
            "jobs": len([fact for fact in jobs if fact.get("availability") == "available"]),
            "updates": len([fact for fact in activity if fact.get("type") == "company_update" and fact.get("availability") == "available"]),
            "social": len([fact for fact in activity if fact.get("type") == "social_profile" and fact.get("availability") == "available"]),
        },
    }


def build_v2_html(rows: list[dict[str, Any]], title: str = "Signalpost V2") -> str:
    companies = [compact_company(row) for row in rows]
    payload = json.dumps(companies, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page_title = html.escape(title)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
<style>
:root{{--bg:#f3f4f0;--card:#fff;--ink:#17211d;--muted:#68736d;--line:#dce2de;--accent:#174c3c;--soft:#e9f2ee;--warn:#8a651c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif}}a{{color:var(--accent);overflow-wrap:anywhere}}button,input{{font:inherit}}.top{{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);padding:14px 22px;display:flex;justify-content:space-between;gap:14px;align-items:center}}.brand{{font-weight:800;font-size:18px}}.brand b{{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:8px;background:var(--accent);color:#fff;margin-right:8px}}.top small{{color:var(--muted)}}.hero{{max-width:1500px;margin:auto;padding:28px 22px 16px}}h1{{font-size:clamp(32px,5vw,58px);line-height:1.02;margin:5px 0 12px;letter-spacing:-.03em}}.hero p{{max-width:900px;color:var(--muted);font-size:16px}}.boundary{{max-width:1000px;padding:10px 12px;background:#fff8e8;border-left:3px solid var(--warn)}}.summary{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:18px}}.metric,.panel,.area{{background:var(--card);border:1px solid var(--line);border-radius:12px}}.metric{{padding:11px}}.metric strong{{display:block;font-size:22px}}.metric span{{font-size:11px;color:var(--muted)}}.layout{{max-width:1500px;margin:auto;padding:0 22px 44px;display:grid;grid-template-columns:280px minmax(0,1fr);gap:14px;align-items:start}}.panel{{min-width:0}}.index{{position:sticky;top:70px;overflow:hidden}}.search{{padding:12px;border-bottom:1px solid var(--line)}}.search input{{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px}}.list{{max-height:calc(100vh - 145px);overflow:auto}}.company{{display:block;width:100%;border:0;border-bottom:1px solid var(--line);background:#fff;text-align:left;padding:10px 12px;cursor:pointer}}.company:hover,.company.active{{background:var(--soft)}}.company strong,.company small{{display:block}}.company small{{color:var(--muted)}}.profile{{padding:18px}}.profile-head{{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap}}h2{{font-size:32px;line-height:1.08;margin:3px 0}}.org{{font-family:ui-monospace,monospace;color:var(--muted)}}.badges{{display:flex;gap:5px;flex-wrap:wrap}}.badge{{font-size:10px;border:1px solid var(--line);padding:3px 7px;border-radius:999px}}.badge.on{{background:var(--soft);border-color:#b9d5c8;color:var(--accent)}}.brief{{margin:14px 0;padding:12px;background:#f8faf8;border:1px solid var(--line);border-radius:10px}}.areas{{display:grid;grid-template-columns:1fr;gap:10px}}.area{{padding:13px;min-width:0}}.area h3{{margin:0 0 8px;font-size:18px}}.area-head{{display:flex;justify-content:space-between;gap:10px;align-items:center}}.facts{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}}.fact{{border:1px solid var(--line);border-radius:9px;padding:9px;min-width:0}}.fact .label{{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}}.fact .value{{font-weight:650;margin:3px 0;overflow-wrap:anywhere}}.fact .meta{{font-size:10px;color:var(--muted)}}details{{margin-top:6px;font-size:11px}}summary{{cursor:pointer;color:var(--accent);font-weight:700}}code{{font-size:9px;word-break:break-all}}.empty{{padding:9px;background:#faf8f1;border-radius:8px;color:var(--muted)}}.ops{{border-top:1px solid var(--line);margin-top:15px;padding-top:10px;color:var(--muted);font-size:11px}}@media(max-width:900px){{.layout{{grid-template-columns:1fr}}.index{{position:static}}.list{{max-height:300px}}.summary{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:560px){{.top,.hero,.layout{{padding-left:12px;padding-right:12px}}.top{{flex-wrap:wrap}}.summary,.facts{{grid-template-columns:1fr}}.profile{{padding:12px}}h2{{font-size:27px}}}}
</style></head>
<body><header class="top"><div class="brand"><b>S</b>Signalpost V2</div><small>Evidence-linked canonical company intelligence</small></header>
<div class="hero"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);font-weight:800">Builderr canonical view</div><h1>One company record. Five traceable data areas.</h1><p>Registry and accounts facts are mapped into explicit canonical fields. Verified first-party website, contact, social, job and dated update facts remain bounded by source evidence.</p><div class="boundary"><strong>Evidence boundary:</strong> missing values are not inferred. A generic careers page is not a hiring fact. A social URL means the verified company page declared it; platform activity or ownership is not inferred.</div><div class="summary" id="summary"></div></div>
<div class="layout"><aside class="panel index"><div class="search"><input id="q" type="search" placeholder="Search company, org number, municipality"><small id="match"></small></div><div class="list" id="list"></div></aside><main class="panel profile" id="profile"></main></div>
<script>
const DATA={payload};
const AREAS=[['company_record','Company record'],['financials','Financials'],['people_and_locations','People & locations'],['company_website','Company website'],['hiring_and_public_activity','Hiring & public activity']];
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])),norm=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();let selected=DATA[0]?.org||null;
function val(v){{if(v===null||v===undefined||v==='')return 'Not published';if(typeof v==='object')return JSON.stringify(v);if(typeof v==='number')return new Intl.NumberFormat('en-US').format(v);return String(v)}}
function evidence(f){{if(!f.evidence?.length)return '';return f.evidence.map(e=>`<details><summary>Evidence</summary><div><a href="${{esc(e.url)}}" target="_blank" rel="noreferrer">${{esc(e.url)}}</a></div><div>${{esc(e.sourceClass||'source')}} · retrieved ${{esc(e.retrievedAt||'not reported')}}${{e.effectiveAt?` · effective ${{esc(e.effectiveAt)}}`:''}}</div>${{e.span?`<div>${{esc(e.span)}}</div>`:''}}${{e.hash?`<code>${{esc(e.hash)}}</code>`:''}}</details>`).join('')}}
function fact(f){{let p=f.period?` · period ${{esc(typeof f.period==='object'?JSON.stringify(f.period):f.period)}}`:'';let c=f.currency?` · ${{esc(f.currency)}}`:'';return `<div class="fact"><div class="label">${{esc(f.field||f.type)}}</div><div class="value">${{esc(val(f.value))}}</div><div class="meta">${{esc((f.availability||'unknown').replaceAll('_',' '))}}${{c}}${{p}}${{f.platform?` · ${{esc(f.platform)}}`:''}}</div>${{f.scope?`<div class="meta">${{esc(f.scope)}}</div>`:''}}${{evidence(f)}}</div>`}}
function renderSummary(){{const areaCounts=Object.fromEntries(AREAS.map(([k])=>[k,DATA.filter(x=>x.areaAvailability?.[k]).length]));$('#summary').innerHTML=AREAS.map(([k,l])=>`<div class="metric"><strong>${{areaCounts[k]}}</strong><span>${{esc(l)}} / ${{DATA.length}}</span></div>`).join('')}}
function renderList(){{let q=norm($('#q').value),rows=DATA.filter(x=>!q||norm(`${{x.name}} ${{x.org}} ${{x.municipality||''}}`).includes(q));$('#match').textContent=`${{rows.length}} of ${{DATA.length}} companies`;$('#list').innerHTML=rows.map(x=>`<button class="company ${{x.org===selected?'active':''}}" data-org="${{esc(x.org)}}"><strong>${{esc(x.name)}}</strong><small>${{esc(x.org)}}${{x.municipality?` · ${{esc(x.municipality)}}`:''}}</small></button>`).join('');document.querySelectorAll('.company').forEach(b=>b.onclick=()=>{{selected=b.dataset.org;renderList();renderProfile()}})}}
function renderProfile(){{let x=DATA.find(v=>v.org===selected)||DATA[0];if(!x)return;let badges=AREAS.map(([k,l])=>`<span class="badge ${{x.areaAvailability?.[k]?'on':''}}">${{esc(l)}}: ${{x.areaAvailability?.[k]?'available':'not published'}}</span>`).join('');let facts=x.areas.company_record||[];let industry=facts.find(f=>f.type==='industry'&&f.availability==='available');let workforce=facts.find(f=>f.type==='workforce_snapshot'&&f.availability==='available');let brief=[industry?`Industry: ${{val(industry.value)}}.`:'Industry not published.',workforce?`Workforce snapshot: ${{val(workforce.value)}}.`:'Workforce snapshot not published.',x.counts.jobs?`${{x.counts.jobs}} strict job posting(s).`:'No strict job posting published.',x.counts.updates?`${{x.counts.updates}} dated company update(s).`:'No dated company update published.'].join(' ');$('#profile').innerHTML=`<div class="profile-head"><div><div class="org">${{esc(x.org)}}</div><h2>${{esc(x.name)}}</h2><div>${{esc(x.municipality||'Municipality not published')}}</div></div><div class="badges">${{badges}}</div></div><div class="brief"><strong>Evidence-bounded brief</strong><div>${{esc(brief)}}</div></div><div class="areas">${{AREAS.map(([k,l])=>{{let fs=x.areas[k]||[];return `<section class="area"><div class="area-head"><h3>${{esc(l)}}</h3><span class="badge ${{x.areaAvailability?.[k]?'on':''}}">${{fs.filter(f=>f.availability==='available').length}} facts</span></div>${{fs.length?`<div class="facts">${{fs.map(fact).join('')}}</div>`:`<div class="empty">No qualified facts published for this area.</div>`}}</section>`}}).join('')}}</div><div class="ops">Run ${{esc(x.run?.run_id||'n/a')}} · terminal ${{esc(x.run?.terminal_status||'n/a')}} · requests ${{esc(x.operations?.requests??'n/a')}} · third-party cost ${{esc(x.operations?.third_party_cost_usd??'n/a')}}</div>`}}
$('#q').addEventListener('input',renderList);renderSummary();renderList();renderProfile();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Signalpost V2's evaluator-facing canonical product surface.")
    parser.add_argument("--input", required=True, help="V2 output-contract JSONL")
    parser.add_argument("--output", required=True, help="HTML product output")
    parser.add_argument("--title", default="Signalpost V2 — evidence-backed company intelligence")
    parser.add_argument("--expect-count", type=int)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    if args.expect_count is not None and len(rows) != args.expect_count:
        raise SystemExit(f"expected {args.expect_count} rows, got {len(rows)}")
    body = build_v2_html(rows, title=args.title)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    print(json.dumps({"companies": len(rows), "output": str(output), "bytes": len(body.encode('utf-8')), "data_linked": True}, indent=2))


if __name__ == "__main__":
    main()
