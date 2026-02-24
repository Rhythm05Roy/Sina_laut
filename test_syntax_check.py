import ast, sys
files = [
    "app/services/keyword_crawler.py",
    "app/services/dataforseo_client.py",
]
all_ok = True
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            src = fh.read()
        ast.parse(src)
        print(f"SYNTAX OK: {f}")
    except SyntaxError as e:
        print(f"SYNTAX ERROR in {f}: {e}")
        all_ok = False
sys.exit(0 if all_ok else 1)
