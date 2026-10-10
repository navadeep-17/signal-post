#!/usr/bin/env python3
"""M38 Actions-only consumed-four archive and encrypted-report wrapper.

PREVIEW mode: read only prior GitHub artifacts, verify frozen profiles and
decrypt two existing ciphertext reports in memory, compile exactly the fixed
alternate query. Absolutely zero provider/company HTTP.
LIVE mode: separately authorized manual branch run only, attempt <=4 Basic
searches using the single prechosen alternate query and <=8 site logical
requests, encrypt the result IN MEMORY and write only ciphertext.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]

from run_v10_m26_consumed_pilot import load_consumed_cohort
from run_v10_m33_consumed4_diagnostic import _assert_frozen_history
from run_v10_m38_pre_registered_pilot import _validate_previous_four,run_m38
from norway_company_agent.v10_m38_alternative_search import _single_alternative_body

REPO="navadeep-17/signal-post"
BRANCH_REF="refs/heads/experiment/v10-m38-pre-registered-4-homepage-query"
ARTIFACTS={
    "m19-a":11505218381,
    "m19-b":11525046472,
    "m20-a":11525304908,
    "old-20-encrypted":11589949864,
    "old-4-encrypted":11592869227,
}
CIPHERTEXT_FILE="m38-private-consumed-four-ciphertext.fernet"
CIPHERTEXT_ARTIFACT_NAME="m38-private-encrypted-consumed-four"


def _get_existing_artifact(artifact_id:int, path:Path,token:str) -> None:
    if not token or artifact_id not in ARTIFACTS.values():
        raise ValueError("Unapproved artifact download")
    endpoint=f"https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}/zip"
    result=subprocess.run([
        "curl","--fail","--silent","--show-error","--location","--retry","2",
        "--connect-timeout","15","--max-time","100",
        "-H","Authorization: Bearer "+token,
        "-H","Accept: application/vnd.github+json",endpoint,"-o",str(path)
    ],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    if result.returncode:
        raise ValueError("Existing pinned evidence retrieval failed")


def _decrypt_one(path:Path,filename:str,fernet) -> dict:
    with ZipFile(path) as archive:
        assert archive.namelist()==[filename], "Unexpected ciphertext archive members"
        assert 100 < archive.getinfo(filename).file_size < 1_000_000
        ciphertext=archive.read(filename)
    if not ciphertext.startswith(b"gAAAA"):
        raise ValueError("Not previously encrypted Fernet data")
    result=json.loads(fernet.decrypt(ciphertext))
    if not isinstance(result,dict):
        raise ValueError("Historical encrypted report not a dictionary")
    return result


def _refuse_prior_live_report(token:str,temporary_directory:Path) -> None:
    """Prevent new manual dispatch of the same four-credit experiment.

    API reports all existing artifacts by exact name, including an incomplete
    previous run. If the check fails we stop rather than guessing.
    """
    dest=temporary_directory/"existing-m38-artifacts.json"
    endpoint=(f"https://api.github.com/repos/{REPO}/actions/artifacts"
              f"?name={CIPHERTEXT_ARTIFACT_NAME}&per_page=100")
    result=subprocess.run([
        "curl","--fail","--silent","--show-error","--location",
        "--connect-timeout","15","--max-time","30",
        "-H","Authorization: Bearer "+token,
        "-H","Accept: application/vnd.github+json",endpoint,"-o",str(dest)
    ],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=40)
    if result.returncode:
        raise ValueError("Cannot verify no earlier M38 live artifact")
    listing=json.loads(dest.read_bytes())
    if not isinstance(listing,dict) or not isinstance(listing.get("total_count"),int):
        raise ValueError("Prior M38 live-run check returned unknown schema")
    if listing["total_count"]!=0:
        raise ValueError("M38 already produced an encrypted report; no duplicate search")


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    run=parser.add_mutually_exclusive_group(required=True)
    run.add_argument("--preview",action="store_true")
    run.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if (
        os.environ.get("GITHUB_REPOSITORY")!=REPO or
        os.environ.get("GITHUB_REF")!=BRANCH_REF or
        os.environ.get("GITHUB_EVENT_NAME") not in ("push","workflow_dispatch")
    ):
        raise ValueError("M38 requires exact experimental repository and ref")
    if args.live and (
        os.environ.get("GITHUB_EVENT_NAME")!="workflow_dispatch" or
        os.environ.get("GITHUB_RUN_ATTEMPT")!="1"
    ):
        raise ValueError("M38 LIVE requires first-attempt manual workflow only")

    token=os.environ.get("GH_TOKEN","")
    from cryptography.fernet import Fernet
    encryption=os.environ.get("SIGNALPOST_PILOT_REPORT_KEY","")
    if not encryption:
        raise ValueError("Private historical report encryption secret missing")
    fernet=Fernet(encryption.encode())

    with tempfile.TemporaryDirectory(prefix="m38-consumed-readonly-") as folder:
        directory=Path(folder)
        archives={}
        for name,artifact_id in ARTIFACTS.items():
            path=directory/(name+".zip")
            _get_existing_artifact(artifact_id,path,token)
            archives[name]=path
        profiles=load_consumed_cohort(
            [archives[name] for name in ("m19-a","m19-b","m20-a")],
            ROOT/"evaluation/v10_m24_consumed_dev_20.json",
        )
        previous20=_decrypt_one(
            archives["old-20-encrypted"],"m30-rescued-encrypted-report.fernet",fernet
        )
        previous4=_decrypt_one(
            archives["old-4-encrypted"],"m33-frozen-four-ciphertext.fernet",fernet
        )
        frozen_four=_assert_frozen_history(profiles,previous20)
        _validate_previous_four(frozen_four,previous4)
        # Validate every real consumed company can compile exactly the
        # approved query *before* allowing live provider requests.
        for profile in frozen_four:
            body=_single_alternative_body(profile)
            assert body["search_depth"]=="basic" and body["max_results"]<=10
            assert body["include_answer"] is False
        if args.preview:
            report=run_m38(profiles,previous20,previous4,live=False)
            assert report["query_alt_diagnostic"]["attempted"]==0
            assert report["query_alt_diagnostic"]["reserved_logical_http"]==0
            print("M38 PREVIEW PASS: exact historical 4, one compiled query each, zero searches/pages")
            return 0

        _refuse_prior_live_report(token,directory)
        provider_key=os.environ.get("TAVILY_API_KEY","")
        if not provider_key:
            raise ValueError("Live requires server-side provider secret")
        report=run_m38(profiles,previous20,previous4,live=True,api_key=provider_key)
        alt=report["query_alt_diagnostic"]
        assert alt["requested"]==4 and 0<=alt["attempted"]<=4
        assert alt["reserved_logical_http"]<=12
        assert alt["reserved_conservative_challenge_charge"]<=24
        assert report["published_company_claims"]==0
        assert report["fresh_holdout_used"] is False
        assert report["production_modified"] is False
        ciphertext=fernet.encrypt(json.dumps(report,sort_keys=True).encode())
        output=Path(os.environ.get("RUNNER_TEMP","/tmp"))/CIPHERTEXT_FILE
        output.write_bytes(ciphertext)
        output.chmod(0o600)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"],"a") as handle:
                handle.write("aborted="+str(alt["aborted"]).lower()+"\n")
        print("M38: frozen-four private development report ENCRYPTED, zero published claims")
        return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Provider response bodies, secrets, candidate names and URLs must not
        # enter public Actions logs even if the encrypted audit fails.
        print("M38 guard failed; no provider/company details released")
        raise SystemExit(1)
