#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
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
        canonical = row.get("canonical")
        if not isinstance(canonical, dict):
            raise ValueError(f"Missing canonical projection at {path}:{line_no}")
        rows.append(row)
    return rows


def compact(row: dict[str, Any]) -> dict[str, Any]:
    evidence = {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    canonical = row["canonical"]

    def decorate(fact: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(fact, dict):
            return None
        refs = [evidence[eid] for eid in fact.get("evidence_ids") or [] if eid in evidence]
        return {
            **fact,
            "sources": [
                {
                    "id": ref.get("id"),
                    "url": ref.get("source_url"),
                    "source_class": ref.get("source_class"),
                    "retrieved_at": ref.get("retrieved_at"),
                    "effective_at": ref.get("effective_at"),
                    "span": ref.get("claim_span"),
                    "sha256": ref.get("content_sha256"),
                }
                for ref in refs
            ],
        }

    company = {
        key: decorate(value)
        for key, value in (canonical.get("company") or {}).items()
    }
    accounts = canonical.get("accounts") or {}
    financials = {
        key: [decorate(fact) for fact in values or []]
        for key, values in (accounts.get("financials") or {}).items()
    }
    web = canonical.get("web") or {}
    return {
        "org": str(row.get("organisation_number") or ""),
        "schema": canonical.get("schema_version"),
        "run": row.get("run") or {},
        "operations": row.get("operations") or {},
        "changes": row.get("changes") or [],
        "company": company,
        "accounts": {
            "latest_submitted": decorate(accounts.get("latest_submitted")),
            "accounting_obligation": decorate(accounts.get("accounting_obligation")),
            "financials": financials,
        },
        "people": [decorate(fact) for fact in canonical.get("people") or []],
        "locations": [decorate(fact) for fact in canonical.get("locations") or []],
        "workforce": [decorate(fact) for fact in canonical.get("workforce") or []],
        "web": {
            "official_website": decorate(web.get("official_website")),
            "company_description": decorate(web.get("company_description")),
            "contact_emails": [decorate(fact) for fact in web.get("contact_emails") or []],
            "social_profiles": [decorate(fact) for fact in web.get("social_profiles") or []],
        },
        "hiring": [decorate(fact) for fact in canonical.get("hiring") or []],
        "public_activity": [decorate(fact) for fact in canonical.get("public_activity") or []],
        "facts": [decorate(fact) for fact in canonical.get("facts") or []],
    }


def build_html(rows: list[dict[str, Any]], title: str) -> str:
    payload = json.dumps([compact(row) for row in rows], ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    safe_title = html.escape(title)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}</title>
<style>
:root{{--bg:#f5f3ee;--card:#fff;--ink:#171717;--muted:#6c6b67;--line:#dedbd2;--accent:#253b80;--soft:#eef1fb;--ok:#19633e;--warn:#8a5a10}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,sans-serif}}a{{color:var(--accent);overflow-wrap:anywhere}}
header{{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid var(--line);padding:14px 20px;display:flex;justify-content:space-between;gap:12px;align-items:center}}header strong{{font-size:17px}}header small{{color:var(--muted)}}
.hero{{max-width:1460px;margin:auto;padding:28px 20px 18px}}h1,h2,h3{{margin:0}}h1{{font-size:clamp(32px,5vw,58px);line-height:1.02;max-width:900px}}.hero p{{max-width:900px;color:var(--muted);font-size:16px}}.boundary{{border-left:4px solid var(--accent);background:var(--soft);padding:10px 13px;max-width:1000px}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:18px}}.stat,.panel,.tile{{background:var(--card);border:1px solid var(--line)}}.stat{{padding:12px}}.stat b{{display:block;font-size:24px}}
.shell{{max-width:1460px;margin:auto;padding:0 20px 40px;display:grid;grid-template-columns:280px minmax(0,1fr);gap:14px;align-items:start}}.panel{{min-width:0}}.index{{position:sticky;top:64px;max-height:calc(100vh - 82px);overflow:hidden}}.search{{padding:12px;border-bottom:1px solid var(--line)}}input{{width:100%;padding:9px;border:1px solid var(--line);font:inherit}}.list{{max-height:calc(100vh - 145px);overflow:auto}}button.row{{display:block;width:100%;padding:10px 12px;border:0;border-bottom:1px solid var(--line);background:#fff;text-align:left;cursor:pointer}}button.row:hover,button.row.active{{background:var(--soft)}}button.row small{{display:block;color:var(--muted)}}
.profile{{padding:18px}}.profile-head{{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:15px}}.profile-head h2{{font-size:32px}}.muted{{color:var(--muted)}}.chips{{display:flex;gap:5px;flex-wrap:wrap}}.chip{{padding:3px 7px;border:1px solid var(--line);border-radius:999px;font-size:11px}}.chip.ok{{color:var(--ok)}}.chip.warn{{color:var(--warn)}}
section{{padding:17px 0;border-bottom:1px solid var(--line)}}section h3{{margin-bottom:9px;font-size:19px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.tile{{padding:10px;min-width:0}}.tile span{{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}}.tile b{{display:block;margin-top:3px;overflow-wrap:anywhere}}.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}}.item{{padding:10px;border:1px solid var(--line);min-width:0;overflow-wrap:anywhere}}.item pre{{white-space:pre-wrap;word-break:break-word;margin:4px 0;font:12px/1.4 ui-monospace,monospace}}table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12px}}th,td{{padding:7px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{color:var(--muted);width:24%}}details{{margin-top:6px}}summary{{cursor:pointer;color:var(--accent)}}code{{font-size:10px;word-break:break-all}}.empty{{padding:10px;background:#faf8f2;color:var(--muted);border-left:3px solid var(--warn)}}
@media(max-width:850px){{.shell{{grid-template-columns:1fr}}.index{{position:static;max-height:none}}.list{{max-height:300px}}.stats{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:520px){{header,.hero,.shell{{padding-left:12px;padding-right:12px}}header{{flex-wrap:wrap}}.stats,.grid,.cards{{grid-template-columns:1fr}}.profile{{padding:12px}}}}
</style></head><body>
<header><strong>Signalpost · canonical intelligence</strong><small id="runMeta"></small></header>
<div class="hero"><h1>Company facts mapped to evidence, not guesses.</h1><p>Official registry and accounts, people, locations, workforce and bounded first-party web signals are exposed through the same canonical object the evaluator receives.</p><div class="boundary"><b>Claim boundary:</b> missing values are not zero. Declared social URLs do not imply platform ownership or activity. Hiring remains empty unless a concrete role card, job-feed item or apply action is evidenced. Generic careers pages are not hiring facts.</div><div class="stats" id="stats"></div></div>
<div class="shell"><aside class="panel index"><div class="search"><input id="q" placeholder="Search company, org, municipality, industry"><small id="count"></small></div><div class="list" id="list"></div></aside><main class="panel profile" id="profile"></main></div>
<script>
const DATA={payload};let selected=DATA[0]||null;const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const available=f=>f&&f.availability==='available';const value=f=>available(f)?f.value:null;const txt=v=>v==null?'Not published':typeof v==='object'?JSON.stringify(v):String(v);const money=f=>available(f)?new Intl.NumberFormat('en-US',{{maximumFractionDigits:0}}).format(f.value)+' '+(f.currency||''): 'Not published';
function source(f){{if(!f||!f.sources||!f.sources.length)return'';return f.sources.map(s=>`<details><summary>Evidence</summary>${{s.url?`<a href="${{esc(s.url)}}" target="_blank" rel="noreferrer">${{esc(s.url)}}</a>`:''}}<div class="muted">${{esc(s.source_class||'source')}} · retrieved ${{esc(s.retrieved_at||'unknown')}}${{s.effective_at?` · effective ${{esc(s.effective_at)}}`:''}}</div>${{s.span?`<div>${{esc(s.span)}}</div>`:''}}${{s.sha256?`<code>${{esc(s.sha256)}}</code>`:''}}</details>`).join('')}}
function tile(label,f,format=txt){{return `<div class="tile"><span>${{esc(label)}}</span><b>${{esc(format(value(f)))}}</b>${{source(f)}}</div>`}}
function displayName(x){{return value(x.company.legal_name)||x.org}}function industryText(f){{const v=value(f);if(!v)return'Not published';return [v.code,v.label].filter(Boolean).join(' · ')}}function addrText(f){{const v=value(f);if(!v)return'Not published';if(typeof v!=='object')return String(v);return [...(v.adresse||[]),v.postnummer,v.poststed,v.kommune].filter(Boolean).join(', ')}}
function socialCount(x){{return x.web.social_profiles.length}}function contactCount(x){{return x.web.contact_emails.length}}
function renderStats(){{const site=DATA.filter(x=>available(x.web.official_website)).length,industry=DATA.filter(x=>available(x.company.industry)).length,work=DATA.filter(x=>x.workforce.length).length,social=DATA.filter(x=>socialCount(x)).length;$('#stats').innerHTML=[[DATA.length,'companies'],[industry,'industry facts'],[work,'workforce facts'],[site,'verified websites'],[social,'social-profile companies']].map(([n,l])=>`<div class="stat"><b>${{n}}</b><span>${{l}}</span></div>`).join('')}}
function renderList(){{const q=$('#q').value.toLowerCase().trim();const rows=DATA.filter(x=>{{const hay=[displayName(x),x.org,value(x.company.municipality),industryText(x.company.industry)].join(' ').toLowerCase();return hay.includes(q)}});$('#count').textContent=`${{rows.length}} shown`;$('#list').innerHTML=rows.map(x=>`<button class="row ${{selected&&selected.org===x.org?'active':''}}" data-org="${{x.org}}"><b>${{esc(displayName(x))}}</b><small>${{esc(x.org)}} · ${{esc(value(x.company.municipality)||'municipality not published')}}</small></button>`).join('');document.querySelectorAll('.row').forEach(b=>b.onclick=()=>{{selected=DATA.find(x=>x.org===b.dataset.org);renderList();renderProfile()}})}}
function factCards(items,empty){{if(!items.length)return`<div class="empty">${{esc(empty)}}</div>`;return `<div class="cards">${{items.map(f=>`<div class="item"><pre>${{esc(txt(value(f)))}}</pre>${{source(f)}}</div>`).join('')}}</div>`}}
function renderProfile(){{if(!selected){{$('#profile').innerHTML='<div class="empty">No companies.</div>';return}}const x=selected,c=x.company,a=x.accounts,w=x.web;const fin=a.financials||{{}};$('#runMeta').textContent=`${{x.schema||'canonical'}} · ${{x.run.terminal_status||'unknown'}}`;$('#profile').innerHTML=`<div class="profile-head"><div><div class="muted">${{esc(x.org)}}</div><h2>${{esc(displayName(x))}}</h2><div class="chips"><span class="chip ${{available(c.industry)?'ok':'warn'}}">industry ${{available(c.industry)?'available':'not published'}}</span><span class="chip ${{available(w.official_website)?'ok':'warn'}}">website ${{available(w.official_website)?'verified':'not published'}}</span><span class="chip ${{x.hiring.length?'ok':'warn'}}">hiring ${{x.hiring.length?'evidenced':'not published'}}</span></div></div><div class="muted">${{esc(x.run.run_id||'')}}</div></div>
<section><h3>Company record</h3><div class="grid">${{tile('Legal form',c.legal_form)}}${{tile('Municipality',c.municipality)}}${{tile('Industry',c.industry,industryText)}}${{tile('Employees',c.employee_count)}}${{tile('Business address',c.business_address,addrText)}}${{tile('Postal address',c.postal_address,addrText)}}${{tile('Bankrupt',c.bankrupt,v=>v===null?'Not published':String(v))}}${{tile('Liquidating',c.liquidating,v=>v===null?'Not published':String(v))}}${{tile('Latest accounts',a.latest_submitted)}}</div></section>
<section><h3>Financials</h3><table>${{[['Revenue','revenue'],['Operating result','operating_result'],['Profit before tax','profit_before_tax'],['Annual result','annual_result'],['Assets','assets'],['Equity','equity'],['Debt','debt']].map(([label,key])=>{{const f=(fin[key]||[])[0];return`<tr><th>${{label}}</th><td>${{esc(money(f))}}${{f&&f.reporting_period?`<div class="muted">${{esc(txt(f.reporting_period))}}</div>`:''}}${{source(f)}}</td></tr>`}}).join('')}}</table></section>
<section><h3>People</h3>${{factCards(x.people,'No people/role facts published.')}}</section><section><h3>Locations</h3>${{factCards(x.locations,'No location facts published.')}}</section><section><h3>Workforce</h3>${{factCards(x.workforce,'No workforce snapshot published.')}}</section>
<section><h3>Verified first-party web</h3><div class="grid">${{tile('Official website',w.official_website)}}${{tile('Description',w.company_description)}}<div class="tile"><span>Contact emails</span><b>${{contactCount(x)}}</b></div></div>${{factCards(w.contact_emails,'No qualifying first-party contact email published.')}}<h3 style="margin-top:14px">Declared social profiles</h3>${{factCards(w.social_profiles,'No declared social-profile facts published.')}}</section>
<section><h3>Hiring</h3>${{factCards(x.hiring,'No concrete role card, job-feed item or apply action published. A generic careers page is intentionally insufficient.')}}</section><section><h3>Public activity</h3>${{factCards(x.public_activity,'No qualifying dated public-activity fact published.')}}</section>
<section><h3>Run & refresh</h3><div class="grid"><div class="tile"><span>Requests</span><b>${{esc(x.operations.requests??0)}}</b></div><div class="tile"><span>Runtime</span><b>${{esc(x.operations.runtime_ms??'unknown')}} ms</b></div><div class="tile"><span>Third-party cost</span><b>$${{esc(x.operations.third_party_cost_usd??0)}}</b></div></div>${{x.changes.length?factCards(x.changes,''):'<div class="empty">No changes emitted in this run.</div>'}}</section>`}}
$('#q').addEventListener('input',renderList);renderStats();renderList();renderProfile();
</script></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Signalpost V2 canonical data-linked product surface.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="Signalpost V2 canonical company intelligence")
    args = parser.parse_args()
    rows = read_jsonl(Path(args.input))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(rows, args.title), encoding="utf-8")
    print(json.dumps({"companies": len(rows), "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
