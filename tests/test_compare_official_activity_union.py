import json
from pathlib import Path

from scripts.compare_official_activity_union import load_source, norm_org


def write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_norm_org():
    assert norm_org("987 654 321") == "987654321"
    assert norm_org("123") is None


def test_source_semantics(tmp_path: Path):
    targets={"111111111","222222222","333333333"}

    p=tmp_path/"support.jsonl"
    write_jsonl(p,[{"organisation_number":"111111111"}])
    a,r=load_source(p,targets,"support")
    assert a=={"111111111"} and r==a

    p=tmp_path/"landbruk.jsonl"
    write_jsonl(p,[
        {"organisation_number":"111111111","positive_support_cells":0},
        {"organisation_number":"222222222","positive_support_cells":2},
    ])
    a,r=load_source(p,targets,"landbruk")
    assert a=={"222222222"} and r==set()

    p=tmp_path/"nfr.jsonl"
    write_jsonl(p,[
        {"organisation_number":"222222222","funded_project_rows":1,
         "current_year_nonterminal_funded_project_rows":0,"recent_start_funded_project_rows":0},
        {"organisation_number":"333333333","funded_project_rows":2,
         "current_year_nonterminal_funded_project_rows":1,"recent_start_funded_project_rows":0},
    ])
    a,r=load_source(p,targets,"forskningsradet")
    assert a=={"222222222","333333333"}
    assert r=={"333333333"}

    p=tmp_path/"doffin.jsonl"
    write_jsonl(p,[
        {"winner_org":"111111111","recent365":False},
        {"winner_org":"333333333","recent365":True},
    ])
    a,r=load_source(p,targets,"doffin")
    assert a=={"111111111","333333333"}
    assert r=={"333333333"}
