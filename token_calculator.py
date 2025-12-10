import os
from pathlib import Path

input_folder = Path("input")

for file in sorted(input_folder.glob("*.txt")):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        chars = len(content)
        # Rough token estimate: ~4 chars per token for English
        estimated_tokens = chars // 4
    print(f"{file.name}: {chars:,} chars, ~{estimated_tokens:,} tokens")