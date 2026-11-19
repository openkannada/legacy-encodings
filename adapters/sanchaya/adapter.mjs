// SPDX-FileCopyrightText: 2026 The Open Kannada Authors
// SPDX-License-Identifier: MIT OR Apache-2.0
//
// The conformance protocol (conformance/README.md) for Sanchaya's kannada-font-converter
// (https://github.com/sanchaya/kannada-font-converter, GPL-3.0). Nothing of it is copied
// here: this program loads its js/app.js from a checkout at run time.
//
//   git clone https://github.com/sanchaya/kannada-font-converter
//   SANCHAYA_JS=$PWD/kannada-font-converter/js/app.js python3 conformance/run.py \
//     --layouts nudi,akruti,shree-lipi,nudi-b,kan-eng --no-detect --no-fonts -- node adapters/sanchaya/adapter.mjs
//
// SANCHAYA_FONTS overrides which of its font types reads each layout, as
// "layout=fontType,...". The converter reports no unknown glyphs or malformed syllables.
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
import vm from "node:vm";

const path = process.env.SANCHAYA_JS;
if (!path) {
  console.error("set SANCHAYA_JS to the converter's js/app.js");
  process.exit(2);
}

// The page script touches the DOM when it loads; any property or call on this stub is a no-op.
const stub = new Proxy(function () {}, {
  get: (_t, key) => (key === Symbol.toPrimitive ? () => "" : stub),
  apply: () => stub,
  construct: () => stub,
});
const context = vm.createContext({
  window: stub, document: stub, localStorage: stub, navigator: stub, location: stub,
  console: { log() {}, warn() {}, error() {}, info() {} }, setTimeout() {}, clearTimeout() {},
  URLSearchParams, TextDecoder, TextEncoder,
});
vm.runInContext(readFileSync(path, "utf8") + "\n;this.__convert = convert;", context);

const fonts = { nudi: "nudi", baraha: "nudi", "shree-lipi": "shree", akruti: "akruti", "nudi-b": "nudi", "kan-eng": "winkey" };
for (const pair of (process.env.SANCHAYA_FONTS || "").split(",").filter(Boolean)) {
  const [layout, font] = pair.split("=");
  fonts[layout] = font;
}
const bilingual = new Set(["nudi-b", "kan-eng"]);
const cp1252 = new TextDecoder("windows-1252");

function respond(req) {
  if (req.op !== "read") return { id: req.id, error: "the converter does not offer this operation" };
  const layout = String(req.layout).toLowerCase();
  const font = fonts[layout];
  if (!font) return { id: req.id, error: `no font type for ${layout}` };
  const bytes = Uint8Array.from(req.codes.split(/\s+/).filter(Boolean), (h) => parseInt(h, 16));
  const digits = req.options && req.options.kannada_digits ? "kn" : "en";
  const text = context.__convert(cp1252.decode(bytes), digits, "a2u", bilingual.has(layout), font);
  return { id: req.id, text, unknown: [], malformed: [] };
}

const lines = createInterface({ input: process.stdin });
for await (const line of lines) {
  if (!line.trim()) continue;
  let req;
  try {
    req = JSON.parse(line);
    process.stdout.write(JSON.stringify(respond(req)) + "\n");
  } catch (e) {
    process.stdout.write(JSON.stringify({ id: req && req.id, error: String(e) }) + "\n");
  }
}
