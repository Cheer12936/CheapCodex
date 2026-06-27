# Cheap Worker Rules For Codex

When a task is mostly reading, summarizing, or boilerplate generation, prefer the cheap worker tools before loading many files into Codex context.

Use:

```bash
ask-worker --paths <files...> --question "<focused question>"
draft-worker --context <reference files...> --target <target> --spec "<draft spec>"
```

Keep reasoning, debugging, architecture, security-sensitive review, and final edits in Codex.

