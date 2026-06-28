# Troubleshooting

## `result.json does not exist`

Check that `--ocr-output` points to the directory containing `result.json`.

## `result.md does not exist`

The converter requires both `result.json` and `result.md`, even though MVP mainly uses `result.json`.

## `Source PDF does not exist`

Check `--source-pdf`. Paths with spaces are supported when quoted.

## `DEEPSEEK_API_KEY is required`

Use `--translate false` for the MVP default path, or set `DEEPSEEK_API_KEY` before selecting the DeepSeek provider.

## Invalid `.bookmd`

Run:

```bash
python -m converter validate path/to/book.bookmd
```

The command reports missing required files.
