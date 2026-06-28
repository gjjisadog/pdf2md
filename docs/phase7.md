# Phase 7 Scope

Phase 7 adds a generic HTTP OCR API adapter while keeping OCR model deployment outside this repository.

## Goals

- Accept a source PDF and call a configurable OCR HTTP API.
- Normalize the OCR API response into the existing `ocr_output/` contract:
  - `result.json`
  - `result.md`
  - `assets/`
  - `parse.log`
- Add a converter CLI `ocr` command.
- Add a converter CLI `build-from-pdf` command that runs OCR first, then builds `.bookmd`.
- Support `--batch-size` and `--max-pages` so real books can be split into small OCR jobs instead of one long whole-PDF job.
- Keep automated tests fully offline with fake transports.

## Generic OCR HTTP Contract

Configuration comes from environment variables:

```bash
export OCR_API_URL=https://example.local/ocr
export OCR_API_KEY=...
export OCR_API_TIMEOUT=120
export OCR_API_DEVICE=gpu
```

The Tailscale/job transport uses:

- `GET /health`
- `POST /v1/ocr/parse`
- `GET /v1/jobs/<job_id>/files/result.md`
- `GET /v1/jobs/<job_id>/files/result.json`
- `GET /v1/jobs/<job_id>/files/source_map.json`
- `GET /v1/jobs/<job_id>/files/parse.log`

The upload request sends `multipart/form-data` with the PDF as `file` and `device` as configured by `OCR_API_DEVICE`.

The expected response is JSON:

```json
{
  "metadata": {
    "title": "Book Title",
    "author": ""
  },
  "blocks": [
    {
      "block_id": "p001_b001",
      "page": 1,
      "type": "paragraph",
      "text": "...",
      "bbox": [72, 120, 510, 180]
    }
  ],
  "assets": []
}
```

Asset entries are optional. This phase supports simple inline assets with `path` and `content_base64`.

## Non-Goals

- No local OCR model deployment.
- No PaddleOCR/PaddleX/PP-StructureV3 install.
- No provider-specific cloud adapter.
- No OCR quality benchmarking.

## Acceptance Criteria

- `python -m pytest` passes.
- OCR client tests do not call the network.
- Missing `OCR_API_URL` fails clearly.
- `python -m converter ocr ...` creates valid `ocr_output` files.
- `python -m converter ocr --batch-size 1 ...` splits, OCRs, and merges page outputs.
- `python -m converter build-from-pdf ...` can produce `.bookmd` from a fake OCR client in tests.
