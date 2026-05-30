"""Tuned prompt on the ISO 27001 held-out set, for the real overfit number."""
import json
from core.eval import run_eval
from examples.quill.prompts.tuned import as_prompts_dict as tuned_prompts_dict
if __name__ == "__main__":
    s = run_eval(example="quill", golden_path="examples/quill/golden/iso27001_holdout.jsonl",
                 prompts=tuned_prompts_dict(), notes="live-session-tuned-iso")
    print(json.dumps(s.__dict__, indent=2))
