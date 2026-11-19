"""Builds the reader review page: 1 offline HTML file with the sample's line images embedded.

Usage: review_page.py SAMPLE.tsv LINES_DIR IMAGES_DIR OUT.html
IMAGES_DIR holds <id>.png, each line drawn with its document's own font (draw.py).
A reader marks each line Same or Different, types the right text where it differs, and
downloads the answers as a TSV (id, verdict, correction, reader) for `sample.py bars`.
"""
import base64
import csv
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Converter check</title>
<style>
:root{--bg:#fff;--fg:#111;--muted:#666;--line:#ddd;--ok:#0a7d38;--bad:#b3261e;--card:#fafafa}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--muted:#aaa;--line:#333;--ok:#4cc27a;--bad:#ff7b72;--card:#1c1c1c}}
body{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;margin:0 auto;max-width:900px;padding:16px}
h1{font-size:22px;margin:8px 0}
.kn{font-family:"Noto Sans Kannada","Kannada Sangam MN","Tunga","Nirmala UI",sans-serif}
.item{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:14px 0;padding:12px}
.item img{background:#fff;display:block;max-width:100%;height:auto;border-radius:4px}
.text{font-size:24px;margin:10px 0;word-break:break-word}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
button{font:inherit;padding:6px 14px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
.item[data-v=right] .same{background:var(--ok);color:#fff;border-color:var(--ok)}
.item[data-v=wrong] .diff{background:var(--bad);color:#fff;border-color:var(--bad)}
input{font:inherit;flex:1;min-width:200px;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
.item:not([data-v=wrong]) .fix{display:none}
.num{color:var(--muted);font-size:13px}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line);z-index:1}
</style></head><body>
<div class="bar row"><strong id="count"></strong><button id="save">Download answers</button><input id="reader" placeholder="Your name (optional)"></div>
<h1>Does the Unicode text match the line?</h1>
<p>Each picture is a line from a Karnataka government document, drawn with the font the document used. Below it is the text in Unicode. Press <b>Same</b> if every letter, digit and punctuation mark matches, including the document's own spelling mistakes. Press <b>Different</b> if any of them differs, and type the line as you see it. Spaces do not matter.</p>
<p class="kn">ಚಿತ್ರದಲ್ಲಿರುವ ಸಾಲು ಮತ್ತು ಅದರ ಕೆಳಗಿನ ಯೂನಿಕೋಡ್ ಪಠ್ಯ ಒಂದೇ ಆಗಿದ್ದರೆ <b>Same</b>, ಯಾವುದೇ ಅಕ್ಷರ ಬೇರೆಯಾಗಿದ್ದರೆ <b>Different</b> ಒತ್ತಿ, ಸರಿಯಾದ ಸಾಲನ್ನು ಬರೆಯಿರಿ.</p>
<p>Your answers stay in this browser until you press <b>Download answers</b>. Send that file back.</p>
__ITEMS__
<script>
const KEY = "converter-check-__SEED__";
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const items = [...document.querySelectorAll(".item")];
function persist() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} update(); }
function update() { const n = items.filter(i => state[i.dataset.id] && state[i.dataset.id].v).length; document.getElementById("count").textContent = n + " of " + items.length + " checked"; }
for (const it of items) {
  const s = state[it.dataset.id] || {};
  if (s.v) it.dataset.v = s.v;
  const fix = it.querySelector(".fix input");
  fix.value = s.fix || "";
  it.querySelector(".same").onclick = () => { it.dataset.v = "right"; state[it.dataset.id] = {v: "right"}; persist(); };
  it.querySelector(".diff").onclick = () => { it.dataset.v = "wrong"; state[it.dataset.id] = {v: "wrong", fix: fix.value}; persist(); fix.focus(); };
  fix.oninput = () => { state[it.dataset.id] = {v: "wrong", fix: fix.value}; persist(); };
}
document.getElementById("save").onclick = () => {
  const who = document.getElementById("reader").value.replace(/[\\t\\n]/g, " ");
  const rows = ["id\\tverdict\\tcorrection\\treader"];
  for (const it of items) { const s = state[it.dataset.id]; if (s && s.v) rows.push([it.dataset.id, s.v, (s.fix || "").replace(/[\\t\\n]/g, " "), who].join("\\t")); }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([rows.join("\\n") + "\\n"], {type: "text/tab-separated-values"}));
  a.download = "converter-check-answers.tsv"; a.click();
};
update();
</script></body></html>
"""


def png_data(path):
    img = Image.open(path).convert("L")
    if img.height > 80:
        img = img.resize((max(1, img.width * 80 // img.height), 80), Image.LANCZOS)
    buf = io.BytesIO()
    img.quantize(colors=16).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    sample_path, lines_dir, images, out = sys.argv[1:5]
    expected = {}
    for path in Path(lines_dir).glob("*.tsv"):
        for r in csv.reader(open(path, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
            if r and not r[0].startswith("#") and r[0] != "id":
                expected[r[0]] = r[3]
    sample = list(csv.DictReader(open(sample_path, encoding="utf-8"), delimiter="\t"))
    parts = []
    for n, row in enumerate(sample, 1):
        lid = row["id"]
        parts.append(
            f'<div class="item" data-id="{html.escape(lid)}"><div class="num">{n}</div>'
            f'<img alt="line {n}" src="data:image/png;base64,{png_data(Path(images) / (lid + ".png"))}">'
            f'<div class="text kn">{html.escape(expected[lid])}</div>'
            '<div class="row"><button class="same">Same</button><button class="diff">Different</button></div>'
            '<div class="row fix"><input class="kn" placeholder="Type the line as it appears"></div></div>'
        )
    seed = json.dumps(len(sample))
    Path(out).write_text(PAGE.replace("__ITEMS__", "\n".join(parts)).replace("__SEED__", seed), encoding="utf-8")


if __name__ == "__main__":
    main()
