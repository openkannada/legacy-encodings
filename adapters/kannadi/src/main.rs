//! kannadi behind the KLE conformance protocol: 1 JSON request per line on stdin,
//! 1 JSON response per line on stdout. A request it cannot answer gets an error.

use std::io::{self, BufRead, Write};

use kannadi::legacy::{
    best_layout, decode_windows_1252, draws_kannada_digits, font_layout, is_legacy_font,
    to_unicode, Layout, Options,
};
use serde_json::{json, Value};

fn codes(req: &Value) -> Result<String, String> {
    let hex = req["codes"].as_str().ok_or("codes must be a string")?;
    let bytes = hex
        .split_whitespace()
        .map(|h| u8::from_str_radix(h, 16).map_err(|_| format!("bad code {h:?}")))
        .collect::<Result<Vec<u8>, String>>()?;
    Ok(decode_windows_1252(&bytes))
}

/// Code point index of a UTF-8 byte offset in `s`, so positions count codes.
fn char_index(s: &str, byte: usize) -> usize {
    s[..byte].chars().count()
}

fn answer(req: &Value) -> Result<Value, String> {
    match req["op"].as_str() {
        Some("read") => {
            let input = codes(req)?;
            let name = req["layout"].as_str().ok_or("layout must be a string")?;
            let layout: Layout = name.parse().map_err(|e| format!("{e}"))?;
            let mut options = Options::default();
            if let Some(v) = req["options"]["zero_as_anusvara"].as_bool() {
                options.zero_as_anusvara = v;
            }
            if let Some(v) = req["options"]["kannada_digits"].as_bool() {
                options.kannada_digits = v;
            }
            let c = to_unicode(&input, layout, &options);
            let unknown: Vec<usize> = c.unknown.iter().map(|u| char_index(&input, u.offset)).collect();
            let malformed: Vec<[usize; 2]> = c
                .malformed
                .iter()
                .map(|r| [char_index(&c.text, r.start), char_index(&c.text, r.end)])
                .collect();
            Ok(json!({"text": c.text, "unknown": unknown, "malformed": malformed}))
        }
        Some("detect") => Ok(json!({"layout": best_layout(&codes(req)?).name()})),
        Some("font") => {
            let name = req["name"].as_str().ok_or("name must be a string")?;
            Ok(json!({
                "layout": font_layout(name).map(Layout::name),
                "legacy": is_legacy_font(name),
                "kannada_digits": draws_kannada_digits(name),
            }))
        }
        other => Err(format!("unknown op {other:?}")),
    }
}

fn respond(line: &str) -> Value {
    let req: Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(e) => return json!({"id": null, "error": format!("bad JSON: {e}")}),
    };
    let mut resp = answer(&req).unwrap_or_else(|e| json!({"error": e}));
    resp["id"] = req["id"].clone();
    resp
}

fn main() -> io::Result<()> {
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for line in io::stdin().lock().lines() {
        writeln!(out, "{}", respond(&line?))?;
        out.flush()?;
    }
    Ok(())
}
