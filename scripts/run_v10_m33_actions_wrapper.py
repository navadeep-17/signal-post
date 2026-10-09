#!/usr/bin/env python3
"""M33 GitHub Actions-only wrapper: pinned old artifacts, zero plaintext report.

No provider requests unless --live is explicitly present and the workflow has
validated exact manual branch/credit confirmation. No CI import side effects.
No Tavily response/snippet, first-party URL or legal ID is printed.
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
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]

from freeze_v10_m24_consumed_dev import SOURCES
from run_v10_m26_consumed_pilot import load_consumed_cohort
from run_v10_m33_consumed4_diagnostic import _assert_frozen_history,diagnostic

ARCHIVE_IDS=(11505218381,11525046472,11525304908)
PREVIOUS_PRIVATE_REPORT_ARTIFACT_ID=11589949864
REPO="navadeep-17/signal-post"
OUTPUT_NAME="m33-frozen-four-ciphertext.fernet"


def get_artifact(id: int, dest: Path, token: str) -> None:
    """Read already-consumed immutable development evidence from GitHub only."""
    if not token or not isinstance(id,int):
        raise ValueError("No authenticated GitHub read-only artifact access")
    url=f"https://api.github.com/repos/{REPO}/actions/artifacts/{id}/zip"
    completed=subprocess.run(
        ["curl","--fail","--silent","--show-error","--location",
         "--retry","2","--connect-timeout","15","--max-time","100",
         "-H","Authorization: Bearer "+token,
         "-H","Accept: application/vnd.github+json",
         url,"-o",str(dest)],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        check=False,timeout=125,
    )
    if completed.returncode:
        raise RuntimeError("Pinned previously consumed artifact retrieval failed")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview",action="store_true")
    mode.add_argument("--live",action="store_true")
    args=p.parse_args()
    if (
        os.environ.get("GITHUB_REPOSITORY")!=REPO
        or os.environ.get("GITHUB_REF")!="refs/heads/experiment/v10-m32-offline-crawl-nomination"
        or os.environ.get("GITHUB_EVENT_NAME")!="workflow_dispatch"
    ):
        raise ValueError("M33 restricted to manual dispatch on exact experimental branch")
    if args.live and os.environ.get("GITHUB_RUN_ATTEMPT")!="1":
        raise ValueError("Duplicate live attempt forbidden")
    token=os.environ.get("GH_TOKEN","")
    with tempfile.TemporaryDirectory(prefix="m33-old-artifacts-") as directory:
        temp=Path(directory)
        zips=[]
        for cohort,source_id in zip(("m19-a","m19-b","m20-a"),ARCHIVE_IDS):
            dst=temp/(cohort+".zip")
            get_artifact(source_id,dst,token)
            zips.append(dst)
        profiles=load_consumed_cohort(zips,ROOT/"evaluation/v10_m24_consumed_dev_20.json")
        assert len(profiles)==20
        if args.preview:
            print("M33: original 20-company cohort verified; zero provider and company HTTP")
            return 0
        from cryptography.fernet import Fernet
        key=os.environ.get("SIGNALPOST_PILOT_REPORT_KEY","")
        provider_key=os.environ.get("TAVILY_API_KEY","")
        if not provider_key or not key:
            raise ValueError("Missing private provider or encryption secret")
        fernet=Fernet(key.encode())
        encrypted_zip=temp/"old-encrypted.zip"
        get_artifact(PREVIOUS_PRIVATE_REPORT_ARTIFACT_ID,encrypted_zip,token)
        with ZipFile(encrypted_zip) as archive:
            if archive.namelist()!=["m30-rescued-encrypted-report.fernet"]:
                raise ValueError("Unknown encrypted historical report archive")
            data=archive.read(archive.namelist()[0])
        if not data.startswith(b"gAAAA") or len(data)>1_000_000:
            raise ValueError("Encrypted historical report integrity guard failed")
        prior=json.loads(fernet.decrypt(data))
        _assert_frozen_history(profiles,prior)  # exactly M31's previously-abstained 17
        report=diagnostic(profiles,prior,live=True,api_key=provider_key)
        assert report["schema"]=="m33_consumed4_funnel_minimal_private_v1"
        assert report["source"]=="PREVIOUSLY_CONSUMED_M24_20_ONLY"
        assert report["requested"]==4
        assert 0<=report["attempted"]<=4
        assert report["reserved_logical_http"]<=12
        assert report["reserved_conservative_challenge_charge"]<=24
        assert report["new_published_claims"]==0
        assert report["qualified_v8_modified"] is False
        ciphertext=fernet.encrypt(json.dumps(report,sort_keys=True).encode())
        out=Path(os.environ.get("RUNNER_TEMP","/tmp"))/OUTPUT_NAME
        out.write_bytes(ciphertext)
        out.chmod(0o600)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"],"a") as fp:
                fp.write("aborted="+str(report["aborted"]).lower()+"\n")
        print("M33: bounded historical four-company diagnostic secured as ciphertext.")
        print("M33: detailed evidence stays private; no company claims or official score.")
        return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # API failures, website exceptions, org IDs, and retrieved content stay out of
        # public GitHub logs; do not print exception strings or tracebacks.
        print("M33 failed closed before/after bounded diagnostic; no private details printed")
        raise SystemExit(1)
