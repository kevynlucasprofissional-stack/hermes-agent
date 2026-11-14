import subprocess
import json
import sys

def eval_hermes(js_code: str):
    res = subprocess.run(
        ["node", "apps/desktop/scripts/eval.mjs", js_code],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    if res.returncode != 0:
        raise RuntimeError(f"eval.mjs failed ({res.returncode}): {res.stderr.strip() or res.stdout.strip()}")
    try:
        return json.loads(res.stdout)
    except Exception:
        return res.stdout.strip()

if __name__ == "__main__":
    test_code = sys.argv[1] if len(sys.argv) > 1 else "1 + 1"
    print(eval_hermes(test_code))
