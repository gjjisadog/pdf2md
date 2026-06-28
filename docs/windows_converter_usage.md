# Windows Converter Usage

Run from the repository root.

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

Required OCR output:

```text
ocr_output/
  result.md
  result.json
  assets/
```

The converter does not run OCR and does not install Paddle-related tooling.
