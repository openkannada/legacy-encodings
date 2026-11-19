// The conformance protocol (conformance/README.md) for Sanka's ASCII to Unicode converter.
//
// Sanka (https://github.com/aravindavk/sanka, MIT) reads Nudi and Baraha ANSI text. Build
// its library first, outside this repository, then point SANKA_JS at it:
//
//   git clone https://github.com/aravindavk/sanka && cd sanka/knjs
//   python3 src/datagen.py > kn.js && cat src/base.js >> kn.js
//   SANKA_JS=$PWD/kn.js python3 conformance/run.py --layouts nudi --no-detect --no-fonts -- node adapters/sanka/adapter.mjs
//
// Sanka reports no unknown glyphs or malformed syllables, so those lists are always empty.
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
import vm from "node:vm";

const path = process.env.SANKA_JS;
if (!path) {
  console.error("set SANKA_JS to Sanka's built kn.js");
  process.exit(2);
}
const context = vm.createContext({});
vm.runInContext(readFileSync(path, "utf8") + "\nthis.Kn = Kn;", context);
const kn = new context.Kn();
const cp1252 = new TextDecoder("windows-1252");

function respond(req) {
  if (req.op !== "read") return { id: req.id, error: "Sanka does not offer this operation" };
  if (!["nudi", "baraha"].includes(String(req.layout).toLowerCase())) {
    return { id: req.id, error: "Sanka reads Nudi and Baraha only" };
  }
  const bytes = Uint8Array.from(req.codes.split(/\s+/).filter(Boolean), (h) => parseInt(h, 16));
  const englishDigits = !(req.options && req.options.kannada_digits);
  const text = kn.ascii_to_unicode(cp1252.decode(bytes), englishDigits, false);
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
