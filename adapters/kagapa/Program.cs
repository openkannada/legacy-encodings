// SPDX-FileCopyrightText: 2026 The Open Kannada Authors
// SPDX-License-Identifier: MIT OR Apache-2.0

// The conformance protocol (conformance/README.md) for KaGaPa's KannadaAsciiUnicodeSDK,
// which reads Nudi and Baraha ANSI text. It reports no unknown glyphs or malformed
// syllables, so those lists are always empty. See README.md here for how to build it.
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Kannada.AsciiUnicode.Converters;

Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
var cp1252 = Encoding.GetEncoding(1252);
var converter = KannadaConverter.Instance;
var stdout = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true };

string? line;
while ((line = Console.ReadLine()) != null)
{
    if (string.IsNullOrWhiteSpace(line)) continue;
    var req = JsonNode.Parse(line)!.AsObject();
    var id = req["id"]?.GetValue<string>();
    var resp = new JsonObject { ["id"] = id };
    try
    {
        var op = req["op"]?.GetValue<string>();
        var layout = req["layout"]?.GetValue<string>()?.ToLowerInvariant();
        if (op != "read") throw new NotSupportedException("the SDK does not offer this operation");
        if (layout != "nudi" && layout != "baraha") throw new NotSupportedException("the SDK reads Nudi and Baraha only");
        var bytes = req["codes"]!.GetValue<string>()
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Select(h => Convert.ToByte(h, 16)).ToArray();
        var kannadaDigits = req["options"]?["kannada_digits"]?.GetValue<bool>() ?? false;
        resp["text"] = converter.ConvertAsciiToUnicode(cp1252.GetString(bytes), convertToEnglishDigit: !kannadaDigits);
        resp["unknown"] = new JsonArray();
        resp["malformed"] = new JsonArray();
    }
    catch (Exception e)
    {
        resp["error"] = e.Message;
    }
    stdout.WriteLine(resp.ToJsonString(new JsonSerializerOptions { Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }));
}
