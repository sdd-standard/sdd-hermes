#!/usr/bin/env python3
"""
check_ids.py — Guarda mecânica 100% passiva (read-only) de identificadores SDD (plugin sdd-hermes).

Port nativo em Python 3 (zero dependências externas) do `check-ids.mjs`.
Detecta:
  - ÓRFÃS: IDs citados (em docs ou código) que não possuem declaração em `docs/sdd/`.
  - NÃO CITADAS: IDs declarados em `docs/sdd/` que ninguém referencia (furo de rastreabilidade).

Suporta nativamente a Paginação Elástica da v2.1 (`10-validation-02.md`, `11-project-memory-02.md`, etc.),
pois todo arquivo dentro de `docs/sdd/` (incluindo `archive/validation-log.md`) é reconhecido como fonte válida de declaração.

Uso via CLI:
  python scripts/check_ids.py [raiz] [--json] [--strict] [--prefixes=ADR,REQ]
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

DEFAULT_PREFIXES = ["VAL", "FR", "NFR", "DES", "TASK", "TSK", "AC", "IB"]

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "out",
    ".next",
    ".turbo",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    "bin",
    "obj",
    ".cache",
    ".pnpm-store",
}

IGNORE_FILE_RE = re.compile(r"^(pnpm-lock|package-lock|yarn\.lock)|\.min\.(js|css)$", re.IGNORECASE)

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
    ".gz", ".tgz", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3",
    ".xlsx", ".docx", ".pptx", ".pyc", ".exe", ".dll", ".so", ".dylib",
}

RE_PLACEHOLDER = re.compile(r"[<{]|\b(nnn|xxx|nn|kk)\b", re.IGNORECASE)
RE_GATE_LOCAL = re.compile(r"[-_]M\d+[-_]\d{1,4}$")
RE_FENCE = re.compile(r"^\s*```")


def _walk_files(root: Path) -> List[Path]:
    collected: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            if IGNORE_FILE_RE.search(fname):
                continue
            full = Path(dirpath) / fname
            if full.suffix.lower() in BINARY_EXTS:
                continue
            try:
                if full.stat().st_size > 2_000_000:
                    continue
            except OSError:
                continue
            collected.append(full)
    return collected


def run_check_ids(
    root: str | Path = ".",
    strict: bool = False,
    extra_prefixes: Sequence[str] | None = None,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    prefixes = list(dict.fromkeys([*DEFAULT_PREFIXES, *(extra_prefixes or [])]))
    prefix_union = "|".join(re.escape(p) for p in prefixes)

    id_core = rf"(?:{prefix_union})(?:[-_][A-Za-z][A-Za-z0-9]{{0,15}})*[-_]\d{{1,4}}"
    re_any = re.compile(id_core)
    re_decl = re.compile(rf"^[#>\-*\s]*({id_core})\s*(?:[—–:-]\s*\S.*)?$")
    re_range = re.compile(rf"({id_core})\s*\.\.\s*(?:(?:{prefix_union})[-_])?(\d{{1,4}})")
    re_trailing_digits = re.compile(r"\d{1,4}$")

    files = _walk_files(root_path)
    declared: Dict[str, str] = {}
    cited: Dict[str, List[str]] = {}

    for file_path in files:
        try:
            # errors="replace": paridade com o check-ids.mjs, que não descarta arquivos fora de UTF-8
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "\x00" in text:
            continue

        rel = file_path.relative_to(root_path).as_posix()
        is_md = file_path.suffix.lower() == ".md"
        decl_source = "docs/sdd/" in rel
        fenced = False

        for idx, line in enumerate(text.splitlines(), start=1):
            if is_md and RE_FENCE.match(line):
                fenced = not fenced
                continue
            where = f"{rel}:{idx}"

            if decl_source and not fenced:
                m_decl = re_decl.match(line)
                if m_decl and not RE_PLACEHOLDER.search(line):
                    decl_id = m_decl.group(1)
                    if decl_id not in declared:
                        declared[decl_id] = where
                    continue

            if is_md and fenced:
                continue
            if RE_PLACEHOLDER.search(line):
                continue

            for m_range in re_range.finditer(line):
                first = m_range.group(1)
                d_match = re_trailing_digits.search(first)
                if not d_match:
                    continue
                digits = d_match.group(0)
                head = first[: len(first) - len(digits)]
                start_n = int(digits)
                end_n = int(m_range.group(2))
                if end_n > start_n and (end_n - start_n) < 200:
                    for n in range(start_n, end_n + 1):
                        expanded_id = f"{head}{str(n).zfill(len(digits))}"
                        cited.setdefault(expanded_id, []).append(where)

            for m_any in re_any.finditer(line):
                found_id = m_any.group(0)
                if decl_source and RE_GATE_LOCAL.search(found_id) and found_id not in declared:
                    declared[found_id] = where
                cited.setdefault(found_id, []).append(where)

    orphans = sorted(
        [
            {"id": cid, "refs": list(dict.fromkeys(refs))}
            for cid, refs in cited.items()
            if cid not in declared
        ],
        key=lambda x: x["id"],
    )
    uncited = sorted(
        [
            {"id": did, "at": loc}
            for did, loc in declared.items()
            if did not in cited
        ],
        key=lambda x: x["id"],
    )

    passed = len(orphans) == 0 and (not strict or len(uncited) == 0)
    return {
        "passed": passed,
        "scanned": len(files),
        "declared": len(declared),
        "citedIds": len(cited),
        "orphans": orphans,
        "uncited": uncited,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    as_json = "--json" in args
    strict = "--strict" in args
    extra_prefixes: List[str] = []
    root = "."

    for arg in args:
        if arg.startswith("--prefixes="):
            raw = arg.split("=", 1)[1]
            extra_prefixes.extend(s.strip() for s in raw.split(",") if s.strip())
        elif not arg.startswith("--"):
            root = arg

    result = run_check_ids(root=root, strict=strict, extra_prefixes=extra_prefixes)

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            f"check-ids: {result['scanned']} arquivos varridos | "
            f"{result['declared']} IDs declarados | {result['citedIds']} citados"
        )
        orphans = result["orphans"]
        if orphans:
            print(f"\nX SIGLAS ORFAS ({len(orphans)}) - citadas mas nunca declaradas:")
            for o in orphans:
                refs = o["refs"]
                head = "\n      ".join(refs[:6])
                more = f"\n      ...(+{len(refs) - 6})" if len(refs) > 6 else ""
                print(f"  {o['id']}\n      {head}{more}")
        else:
            print("\nOK nenhuma sigla orfa.")

        uncited = result["uncited"]
        if uncited:
            marker = "X" if strict else "!"
            print(
                f"\n{marker} DECLARADAS E NUNCA CITADAS ({len(uncited)}) - "
                f"possivel furo de rastreabilidade:"
            )
            for u in uncited:
                print(f"  {u['id']}  (declarada em {u['at']})")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
