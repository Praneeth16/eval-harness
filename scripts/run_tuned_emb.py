"""tuned prompt + current index (gemini embeddings). Arg: soc2 | iso"""
import sys, json
from core.eval import run_eval
from examples.quill.prompts.tuned import as_prompts_dict
which = sys.argv[1] if len(sys.argv) > 1 else "soc2"
golden = ("examples/quill/golden/soc2.jsonl" if which=="soc2"
          else "examples/quill/golden/iso27001_holdout.jsonl")
s = run_eval(example="quill", golden_path=golden, prompts=as_prompts_dict(),
             notes=f"live-session-tuned-gememb-{which}")
print(json.dumps(s.__dict__, indent=2))
