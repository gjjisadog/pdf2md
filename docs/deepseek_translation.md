# DeepSeek Translation

The MVP includes translation boundaries but does not make real DeepSeek calls by default.

Current behavior:

- `--translate false` is the default path.
- `NoopTranslator` preserves block alignment and returns source text.
- `DeepSeekConfig.from_env()` requires `DEEPSEEK_API_KEY` when DeepSeek is selected.

Future DeepSeek implementation must preserve Markdown structure, formulas, variables, units, figure/table numbering, and `block_id`.
