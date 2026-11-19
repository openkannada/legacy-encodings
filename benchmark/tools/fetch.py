"""Fetches the planned PDFs from the Internet Archive, Common Crawl or the live site.

Usage: fetch.py PLAN.tsv [SHARD COUNT]
PLAN rows: document, group, url, fetch location, source (wayback, commoncrawl or live). A
commoncrawl fetch location is commoncrawl:CRAWL@TIMESTAMP. Each PDF is saved as
BENCH_DOWNLOADS/<document>.pdf and logged to BENCH_WORK/fetch-<SHARD>.jsonl with its SHA-256
and archive link. Documents already logged as fetched are skipped, so a run can resume.
SHARD and COUNT split the plan between parallel runs; keep the Internet Archive to 2 runs.
Environment: ONLY (sources to fetch, comma separated), DELAY (seconds between requests),
CURL_TIMEOUT (seconds per download).
"""
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse

from paths import DOWNLOADS, WORK

AGENT = "Mozilla/5.0 (compatible; research crawler)"


def curl(args, timeout):
    return subprocess.run(["curl", "-sL", "-m", str(timeout), "-A", AGENT, *args], capture_output=True).stdout


def complete(body):
    """A whole PDF: the header at the start and an end-of-file marker near the end."""
    return body.startswith(b"%PDF") and b"%%EOF" in body[-65536:]


def from_common_crawl(location, url, timeout):
    crawl, timestamp = location.split(":", 1)[1].split("@")
    query = f"https://index.commoncrawl.org/{crawl}-index?url={urllib.parse.quote(url, safe='')}&output=json"
    best = None
    for line in curl([query], 60).decode(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("status") == "200" and (best is None or rec["timestamp"] == timestamp):
            best = rec
    if not best:
        return None, None
    off, length = int(best["offset"]), int(best["length"])
    record = gzip.decompress(curl(["-r", f"{off}-{off + length - 1}", "https://data.commoncrawl.org/" + best["filename"]], timeout))
    _, rest = record.split(b"\r\n\r\n", 1)
    _, body = rest.split(b"\r\n\r\n", 1)
    archive = f"https://data.commoncrawl.org/{best['filename']} offset {off} length {length} ({crawl}, {best['timestamp']})"
    return body, archive


def fetch(row, timeout):
    doc, group, url, location, source = row
    if source == "commoncrawl":
        body, archive = from_common_crawl(location, url, timeout)
    else:
        body = curl([location], timeout)
        archive = location.replace("id_/", "/") if source == "wayback" else None
    entry = {"doc": doc, "group": group, "url": url, "source": source}
    if body and complete(body):
        (DOWNLOADS / f"{doc}.pdf").write_bytes(body)
        entry.update(status="ok", bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), archive=archive)
    else:
        entry.update(status="not-pdf" if body and not body.startswith(b"%PDF") else "failed", bytes=len(body or b""))
    return entry


def main(argv):
    shard, count = (int(argv[1]), int(argv[2])) if len(argv) > 2 else (0, 1)
    only = set(os.environ["ONLY"].split(",")) if os.environ.get("ONLY") else None
    delay = float(os.environ.get("DELAY", "2"))
    timeout = int(os.environ.get("CURL_TIMEOUT", "600"))
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    done = set()
    for log in WORK.glob("fetch-*.jsonl"):
        done |= {json.loads(l)["doc"] for l in log.open() if json.loads(l)["status"] == "ok"}
    with open(WORK / f"fetch-{shard}.jsonl", "a") as log:
        for line in open(argv[0]):
            row = line.rstrip("\n").split("\t")
            if row[0] in done or int(row[0][1:]) % count != shard or (only and row[4] not in only):
                continue
            try:
                entry = fetch(row, timeout)
            except Exception as e:  # a bad record or a dropped connection; the next run retries it
                entry = {"doc": row[0], "group": row[1], "url": row[2], "source": row[4], "status": "error", "note": str(e)[:200]}
            log.write(json.dumps(entry) + "\n")
            log.flush()
            time.sleep(delay if entry["status"] == "ok" else max(delay, 60))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
