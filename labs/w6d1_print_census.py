r"""labs/w6d1_print_census.py -- Week 6 Din 1 (P-56 census).
Lists every print() call that sits lexically inside an `async with <x>.begin():` block in relay/*.py (or src/*.py),
found by walking the AST rather than by eye. Prints values only; the classification is yours.
Usage: .\.venv\Scripts\python.exe labs\w6d1_print_census.py"""
import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "relay" if (REPO / "relay").exists() else REPO / "src"


def is_begin(item: ast.withitem) -> bool:
    call = item.context_expr
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "begin"
    )


def is_print(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"


inside_total = 0
for path in sorted(SRC.glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    all_prints = sum(1 for n in ast.walk(tree) if is_print(n))
    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncWith) and any(is_begin(i) for i in node.items):
            for sub in ast.walk(node):
                if is_print(sub):
                    inside.add((sub.lineno, node.lineno))
    inside_total += len(inside)
    print(f"file={path.name} prints_total={all_prints} prints_inside_begin={len(inside)}")
    for line, block in sorted(inside):
        print(f"  {path.name}:{line} (inside the begin() block that starts at line {block})")
print(f"prints_inside_begin_total={inside_total}")
