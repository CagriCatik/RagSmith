import re
from pathlib import Path

# configure paths
in_path = Path("md/ocr/A_Compact_Guide_To_RAG.md")
out_path = Path("md/ocr/A_Compact_Guide_To_RAG_cleaned.md")

with in_path.open("r", encoding="utf8") as f:
    original_text = f.read()

original_len = len(original_text)
print(f"Input file: {in_path}")
print(f"Original length: {original_len} characters")

def subn_log(pattern, repl, text, flags=0, label=""):
    new_text, n = re.subn(pattern, repl, text, flags=flags)
    print(f"{label}: {n} replacements")
    return new_text

text = original_text

# 1) remove long dotted leaders (6+ dots) and surrounding spaces
text = subn_log(
    r"\s*\.{6,}\s*",
    " ",
    text,
    label="Dotted leaders removed"
)

# 2) strip trailing spaces/tabs at end of each line
text = subn_log(
    r"[ \t]+$",
    "",
    text,
    flags=re.MULTILINE,
    label="Trailing spaces removed"
)

# 3) remove lines that are only whitespace, pipes, or dots
text = subn_log(
    r"^[\s\|\.]*\n",
    "",
    text,
    flags=re.MULTILINE,
    label="Noise only lines removed"
)

# 4) collapse long runs of internal spaces/tabs to a single space
text = subn_log(
    r"[ \t]{2,}",
    " ",
    text,
    label="Multiple spaces collapsed"
)

# 5) remove standalone page number lines (1--3 digits only)
text = subn_log(
    r"^\s*\d{1,3}\s*$",
    "",
    text,
    flags=re.MULTILINE,
    label="Standalone page numbers removed"
)

# 6) remove horizontal rules made of dashes, underscores, or equals
text = subn_log(
    r"^[\s\-\_=]{3,}\s*$",
    "",
    text,
    flags=re.MULTILINE,
    label="Horizontal rules removed"
)

# 7) unwrap single column table rows like "| text |" or "| text"
text = subn_log(
    r"^\s*\|\s*(.*?)\s*\|?\s*$",
    r"\1",
    text,
    flags=re.MULTILINE,
    label="Table row wrappers removed"
)

# 8) ensure a space after markdown heading markers ("##Heading" -> "## Heading")
text = subn_log(
    r"^(#+)([^\s#])",
    r"\1 \2",
    text,
    flags=re.MULTILINE,
    label="Heading spaces normalized"
)

# 9) collapse 3+ blank lines down to 2
text = subn_log(
    r"\n{3,}",
    "\n\n",
    text,
    label="Blank lines collapsed"
)

# -----------------------------
# Diagnostics on leftovers
# -----------------------------

leftover_dots = len(re.findall(r"\.{6,}", text))
if leftover_dots > 0:
    print(f"Warning: {leftover_dots} long dot runs still present after cleaning.")

leftover_noise_lines = len(re.findall(r"^[\s\|\.]+$", text, flags=re.MULTILINE))
if leftover_noise_lines > 0:
    print(f"Warning: {leftover_noise_lines} noise only lines detected after cleaning.")

leftover_page_lines = len(re.findall(r"^\s*\d{1,3}\s*$", text, flags=re.MULTILINE))
if leftover_page_lines > 0:
    print(f"Warning: {leftover_page_lines} standalone page like lines still present.")

# -----------------------------
# Size and token comparison
# -----------------------------

cleaned_len = len(text)
removed_chars = original_len - cleaned_len
removed_pct = (removed_chars / original_len * 100) if original_len > 0 else 0.0

# simple heuristic: 1 token ~ 4 characters 
orig_tokens_est = round(original_len / 4)
clean_tokens_est = round(cleaned_len / 4)
saved_tokens_est = orig_tokens_est - clean_tokens_est

print(f"Cleaned length: {cleaned_len} characters")
print(f"Characters removed: {removed_chars} ({removed_pct:.2f} percent)")

print(f"Estimated original tokens: {orig_tokens_est} (heuristic)")
print(f"Estimated cleaned tokens: {clean_tokens_est} (heuristic)")
print(f"Estimated tokens saved: {saved_tokens_est} (heuristic)")

with out_path.open("w", encoding="utf8") as f:
    f.write(text)

print(f"Output written to: {out_path}")
