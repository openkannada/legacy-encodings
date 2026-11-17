//! kannadi behind the KLE conformance protocol: 1 JSON request per line on stdin,
//! 1 JSON response per line on stdout.

use std::io::{self, BufRead, Write};

use kannadi::legacy::{
    best_layout, decode_windows_1252, draws_kannada_digits, font_layout, is_legacy_font,
    to_unicode, Layout, Options,
};
use serde_json::{json, Value};

fn codes(req: &Value) -> String {
    let bytes: Vec<u8> = req["codes"]
        .as_str()
        .unwrap_or_default()
        .split_whitespace()
        .map(|h| u8::from_str_radix(h, 16).expect("hex code"))
        .collect();
    decode_windows_1252(&bytes)
}

/// Code point index of each UTF-8 byte offset in `s`, so positions count codes.
fn char_index(s: &str, byte: usize) -> usize {
    s[..byte].chars().count()
}

fn respond(req: &Value) -> Value {
    let id = req["id"].clone();
    match req["op"].as_str() {
        Some("read") => {
            let input = codes(req);
            let layout: Layout = req["layout"].as_str().unwrap_or_default().parse().expect("layout");
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
            json!({"id": id, "text": c.text, "unknown": unknown, "malformed": malformed})
        }
        Some("detect") => json!({"id": id, "layout": best_layout(&codes(req)).name()}),
        Some("font") => {
            let name = req["name"].as_str().unwrap_or_default();
            json!({
                "id": id,
                "layout": font_layout(name).map(Layout::name),
                "legacy": is_legacy_font(name),
                "kannada_digits": draws_kannada_digits(name),
            })
        }
        _ => json!({"id": id, "error": "unknown op"}),
    }
}

fn main() -> io::Result<()> {
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for line in io::stdin().lock().lines() {
        let req: Value = serde_json::from_str(&line?).expect("JSON request");
        writeln!(out, "{}", respond(&req))?;
        out.flush()?;
    }
    Ok(())
}
