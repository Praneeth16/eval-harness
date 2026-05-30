"""One-off live tuned eval — mirrors prebake.py's tuned path.

There is no CLI flag/env to select the tuned prompt variant; the variant is
chosen by passing the tuned `as_prompts_dict()` into `run_eval(prompts=...)`.
This script does exactly that against the SOC 2 golden set so the UI shows a
baseline-vs-tuned contrast.
"""

from __future__ import annotations

import json

from core.eval import run_eval
from examples.quill.prompts.tuned import as_prompts_dict as tuned_prompts_dict

if __name__ == "__main__":
    summary = run_eval(
        example="quill",
        golden_path="examples/quill/golden/soc2.jsonl",
        prompts=tuned_prompts_dict(),
        notes="live-session-tuned",
    )
    print(json.dumps(summary.__dict__, indent=2))
