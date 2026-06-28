# Phase 7 Generic OCR API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic HTTP OCR API adapter that converts a PDF into the existing `ocr_output/` format and can feed the current `.bookmd` builder.

**Architecture:** A new `ocr_client` package owns OCR API config, HTTP transport, response validation, Markdown rendering, and `ocr_output` writing. The converter app owns CLI orchestration through `ocr` and `build-from-pdf` commands. Tests use fake clients/transports and never call a live OCR service.

**Tech Stack:** Python 3.12, pytest, pathlib, json, base64, urllib multipart upload, argparse.

---

## Tasks

- [ ] Add failing OCR client tests for env config, fake transport, and `ocr_output` writing.
- [ ] Implement `packages/ocr_client`.
- [ ] Add failing converter CLI tests for `ocr` and `build-from-pdf`.
- [ ] Wire converter OCR pipeline and CLI commands.
- [ ] Update docs and release verification coverage.
- [ ] Run `python -m pytest` and `python scripts/verify_release.py`.
