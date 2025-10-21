import os
hits = []
for root, _, files in os.walk('backend'):
    for fname in files:
        if fname.endswith(('.py','.env','.ini','.cfg','.json','.yml','.yaml','.txt','.bat','.sh','.ps1','.md','.sql','.toml')):
            path = os.path.join(root, fname)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    for lineno, line in enumerate(fh, 1):
                        if 'sqlite' in line.lower():
                            hits.append((path.replace('\\', '/'), lineno, line.strip()))
            except Exception:
                pass
for path, lineno, text in hits:
    print(f"{path}:{lineno}:{text}")
