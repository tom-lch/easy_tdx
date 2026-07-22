#!/usr/bin/env python3
"""Generate batch-N.json for Vue/TS/frontend batches (uses LLM-style summaries).

These batches contain Vue/TS files where AST analysis isn't sufficient.
We extract component structure heuristically.
"""
import json
import os
import re
import sys

ROOT = "/Users/lichao/work/jytx/easy_tdx"
INTER = f"{ROOT}/.understand-anything/intermediate"


def analyze_frontend_batch(batch_idx):
    batches = json.load(open(f"{INTER}/batches.json"))
    batch = batches["batches"][batch_idx]
    files = batch["files"]

    nodes = []
    edges = []
    file_set = set(f["path"] for f in files)

    for f in files:
        rel_path = f["path"]
        path = os.path.join(ROOT, rel_path)
        if not os.path.exists(path):
            continue
        try:
            with open(path) as fh:
                src = fh.read()
        except Exception:
            continue

        name = os.path.basename(rel_path)
        file_id = f"file:{rel_path}"
        ext = rel_path.split(".")[-1]

        if ext == "vue":
            # Extract component name from filename
            comp_name = name.replace(".vue", "")
            # Look for export default name
            m = re.search(r'name:\s*["\']([^"\']+)["\']', src)
            if m:
                comp_name = m.group(1)
            # Extract template summary
            template_match = re.search(r'<template>(.*?)</template>', src, re.DOTALL)
            template_summary = ""
            if template_match:
                tmpl = template_match.group(1)
                # Take first 200 chars of meaningful template
                template_summary = re.sub(r'\s+', ' ', tmpl)[:300]
            summary = f"Vue 3 component {comp_name}. Template: {template_summary}" if template_summary else f"Vue 3 component {comp_name}."
            tags = ["vue", "frontend", "component", "ui"]
            nodes.append({
                "id": file_id,
                "type": "file",
                "name": name,
                "filePath": rel_path,
                "summary": summary,
                "complexity": min(7, max(2, len(src.split('\n')) // 30)),
                "tags": tags
            })
            # Extract script imports for edge detection
            for imp in re.finditer(r'import\s+(?:\{[^}]+\}|\w+|[^"\']+)\s+from\s+["\']([^"\']+)["\']', src):
                module = imp.group(1)
                if module.startswith("."):
                    # Relative import
                    base = os.path.dirname(rel_path)
                    resolved = os.path.normpath(os.path.join(base, module))
                    # Try with .ts, .vue, /index.ts
                    candidates = [resolved + ".ts", resolved + ".vue", resolved + "/index.ts"]
                    for c in candidates:
                        if c in file_set:
                            edges.append({
                                "source": file_id,
                                "target": f"file:{c}",
                                "type": "imports",
                                "weight": 0.7,
                                "reason": f"{name} imports from {module} (resolves to {c})"
                            })
                            break
        elif ext == "ts":
            # TypeScript module
            summary = f"TypeScript module {name}."
            # Look for export default or top-level exports
            exports = re.findall(r'export\s+(?:default\s+)?(?:class|function|const|interface|type)\s+(\w+)', src)
            if exports:
                summary = f"TypeScript module {name}. Exports: {', '.join(exports[:5])}."
            # First docstring/comment
            doc_match = re.search(r'/\*\*\s*\n([^*]+)\*/', src)
            if doc_match:
                doc = re.sub(r'\s+', ' ', doc_match.group(1)).strip()
                summary = doc[:300] if doc else summary
            tags = ["typescript", "frontend"]
            if "router" in rel_path.lower():
                tags.append("router")
            if "store" in rel_path.lower():
                tags.append("store")
            if "view" in rel_path.lower() or rel_path.endswith("View.vue"):
                tags.append("view")
            if "type" in rel_path.lower():
                tags.append("types")
            nodes.append({
                "id": file_id,
                "type": "file",
                "name": name,
                "filePath": rel_path,
                "summary": summary,
                "complexity": min(7, max(2, len(src.split('\n')) // 30)),
                "tags": tags
            })
            # Imports
            for imp in re.finditer(r'import\s+(?:\{[^}]+\}|\w+|[^"\']+)\s+from\s+["\']([^"\']+)["\']', src):
                module = imp.group(1)
                if module.startswith("."):
                    base = os.path.dirname(rel_path)
                    resolved = os.path.normpath(os.path.join(base, module))
                    candidates = [resolved + ".ts", resolved + ".vue", resolved + "/index.ts"]
                    for c in candidates:
                        if c in file_set:
                            edges.append({
                                "source": file_id,
                                "target": f"file:{c}",
                                "type": "imports",
                                "weight": 0.7,
                                "reason": f"{name} imports from {module}"
                            })
                            break
        elif ext == "css":
            nodes.append({
                "id": file_id,
                "type": "config",
                "name": name,
                "filePath": rel_path,
                "summary": f"Global CSS stylesheet {name}. {len(src.split(chr(10)))} lines of styling rules.",
                "complexity": 2,
                "tags": ["css", "frontend", "styling"]
            })

    return nodes, edges, files


def write_batch(batch_idx, nodes, edges, files):
    out = {
        "schemaVersion": 1,
        "batchIndex": batch_idx,
        "projectRoot": ROOT,
        "filesAnalyzed": [{"path": f["path"], "language": f["language"], "sizeLines": f["sizeLines"], "fileCategory": f["fileCategory"]} for f in files],
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "nodesCreated": len(nodes),
            "edgesCreated": len(edges),
            "complexity": {"min": 1, "max": 7, "avg": 3.0},
            "notes": f"Batch {batch_idx} (frontend Vue/TS) analyzed via regex extraction. {len(nodes)} nodes, {len(edges)} edges."
        }
    }
    out_path = f"{INTER}/batch-{batch_idx}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out_path


if __name__ == "__main__":
    idx = int(sys.argv[1])
    nodes, edges, files = analyze_frontend_batch(idx)
    out = write_batch(idx, nodes, edges, files)
    print(f"Wrote {out}: {len(nodes)} nodes, {len(edges)} edges")