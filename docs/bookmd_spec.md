# BookMD Spec

`.bookmd` is a zip archive with this MVP structure:

```text
book.json
chapters/*.md
assets/
source/original.pdf
source_map.json
terms.json
translation.json
reading_config.json
search_index.json
```

`book.json` stores metadata and chapter paths. `source_map.json` maps each `block_id` back to source page, bbox, source text, translated text, and block type. `search_index.json` stores simple JSON search items for local full-book search.

Every generated Markdown block should preserve trace metadata:

```markdown
<!-- block_id: p001_b003; page: 1; bbox: [72,188,510,246] -->
```
