# KaGaPa KannadaAsciiUnicodeSDK adapter

Runs [KannadaAsciiUnicodeSDK](https://github.com/kagapa-blr/KannadaAsciiUnicodeSDK) (MIT), KaGaPa's C# library for Nudi and Baraha text, behind the conformance protocol. The SDK is not copied here; the build references a checkout of it.

```bash
git clone https://github.com/kagapa-blr/KannadaAsciiUnicodeSDK ../KannadaAsciiUnicodeSDK
dotnet build -c Release adapters/kagapa -p:KagapaSdk=$PWD/../KannadaAsciiUnicodeSDK -o /tmp/kagapa-adapter
python3 conformance/run.py --markdown --layouts nudi --no-detect --no-fonts --timeout 120 -- dotnet /tmp/kagapa-adapter/KagapaAdapter.dll
```

It needs the .NET 8 SDK. The adapter decodes the glyph codes as Windows-1252, calls `KannadaConverter.Instance.ConvertAsciiToUnicode`, and writes Kannada digits only when the request asks for them. The SDK reports no unknown glyphs or malformed syllables, so those lists are always empty.
