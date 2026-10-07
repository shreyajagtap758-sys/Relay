r"""labs/w6d3_interface_check.py -- Week 6 Din 3, Step 1: what the provider module LOOKS like from outside.
Imports one module and lists (1) every class defined in it that has a `complete` method, with its signature and
whether it is a coroutine function, (2) every exception class defined in it, with its bases, (3) whether importing it
pulled in relay.db (which builds the evidence-DB engine at import), and (4) whether a fresh interpreter can import
it with the key variable REMOVED from the environment. Values and labels only (P-52).
Usage: .\.venv\Scripts\python.exe -u labs\w6d3_interface_check.py --module relay.providers [--key-name YOUR_KEY_VAR]"""
import argparse
import importlib
import inspect
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ap = argparse.ArgumentParser()
ap.add_argument("--module", required=True)
ap.add_argument("--key-name", default="")
a = ap.parse_args()

before = set(sys.modules)
mod = importlib.import_module(a.module)
print(f"module={a.module} file={Path(mod.__file__).relative_to(REPO)}")
db_imported = ("relay.db" in sys.modules) or ("src.database" in sys.modules)
print(f"src_database_imported={db_imported} newly_imported_relay="
      + ",".join(sorted(m for m in set(sys.modules) - before if m.startswith("relay."))))
for name, obj in sorted(vars(mod).items()):
    if not inspect.isclass(obj) or obj.__module__ != mod.__name__:
        continue
    if issubclass(obj, BaseException):
        print(f"exception_class={name} bases={','.join(b.__name__ for b in obj.__bases__)}")
    elif hasattr(obj, "complete"):
        fn = getattr(obj, "complete")
        print(f"provider_class={name} complete_is_coroutine={inspect.iscoroutinefunction(fn)} "
              f"signature={inspect.signature(fn)}")
    else:
        print(f"other_class={name}")
if a.key_name:
    env = {k: v for k, v in os.environ.items() if k != a.key_name}
    r = subprocess.run([sys.executable, "-c", f"import {a.module}"], cwd=REPO, env=env, capture_output=True, text=True)
    last = (r.stderr.strip().splitlines() or ["-"])[-1]
    print(f"import_without_{a.key_name}=" + ("ok" if r.returncode == 0 else "fail:" + last.split(":")[0]))
