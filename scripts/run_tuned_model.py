import sys, json
from core.eval import run_eval
from examples.quill.prompts.tuned import as_prompts_dict
model=sys.argv[1]; which=sys.argv[2] if len(sys.argv)>2 else "iso"
golden=("examples/quill/golden/soc2.jsonl" if which=="soc2" else "examples/quill/golden/iso27001_holdout.jsonl")
s=run_eval(example="quill", golden_path=golden, prompts=as_prompts_dict(), model=model, notes=f"cur-port-{model}-{which}")
print(json.dumps(s.__dict__, indent=2))
