#!/usr/bin/env python3
"""Generate batch-N.json for any batch index using AST analysis.

Usage: python3 generate_batch.py <batch_index>
"""
import json
import os
import ast
import sys

ROOT = "/Users/lichao/work/jytx/easy_tdx"
INTER = f"{ROOT}/.understand-anything/intermediate"


def analyze_batch(batch_idx):
    batches = json.load(open(f"{INTER}/batches.json"))
    batch = batches["batches"][batch_idx]
    files = batch["files"]

    nodes = []
    edges = []
    file_set = set(f["path"] for f in files)
    file_nodes_by_id = {}

    for f in files:
        rel_path = f["path"]
        if not rel_path.endswith(".py"):
            continue
        path = os.path.join(ROOT, rel_path)
        if not os.path.exists(path):
            continue
        try:
            with open(path) as fh:
                src = fh.read()
            tree = ast.parse(src)
        except Exception:
            continue

        docstring = (ast.get_docstring(tree) or "").replace("\n", " ").strip()
        name = os.path.basename(rel_path)
        file_id = f"file:{rel_path}"
        summary = docstring[:300] if docstring else f"Python module at {rel_path}."
        tags = ["python", "src", "library"]
        if "/tests/" in rel_path:
            tags = ["python", "tests"]
        elif "/examples/" in rel_path:
            tags = ["python", "example"]
        elif "/scripts/" in rel_path:
            tags = ["python", "script"]
        elif "/strategies/" in rel_path:
            tags = ["python", "strategy"]
        elif "/docs/" in rel_path:
            tags = ["python", "docs"]
        elif "/web-ui/" in rel_path or rel_path.endswith(".vue") or rel_path.endswith(".ts"):
            continue  # skip non-python here

        nodes.append({
            "id": file_id,
            "type": "file",
            "name": name,
            "filePath": rel_path,
            "summary": summary,
            "complexity": min(8, max(1, len(src.split('\n')) // 25)),
            "tags": tags
        })
        file_nodes_by_id[rel_path] = file_id

        # Imports (relative only — for cross-batch, the import_map has them)
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                if n.module and n.level > 0:
                    base_dir = os.path.dirname(rel_path)
                    parts = (n.module or "").split(".")
                    if n.level == 1:
                        target_path = base_dir + "/" + parts[0] + ".py"
                    elif n.level == 2:
                        parent = os.path.dirname(base_dir)
                        target_path = parent + "/" + parts[0] + ".py"
                    elif n.level == 3:
                        grandparent = os.path.dirname(os.path.dirname(base_dir))
                        target_path = grandparent + "/" + parts[0] + ".py"
                    else:
                        target_path = None
                    if target_path and target_path in file_set:
                        target_id = f"file:{target_path}"
                        edges.append({
                            "source": file_id,
                            "target": target_id,
                            "type": "imports",
                            "weight": 0.7,
                            "reason": f"Relative import within batch: from {'.' * n.level}{n.module}"
                        })

        # Classes
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            cls_doc = (ast.get_docstring(cls) or "").replace("\n", " ").strip()
            cls_id = f"class:{rel_path}:{cls.name}"
            cls_summary = cls_doc[:300] if cls_doc else f"Class {cls.name} defined in {rel_path}."
            nodes.append({
                "id": cls_id,
                "type": "class",
                "name": cls.name,
                "filePath": rel_path,
                "summary": cls_summary,
                "complexity": min(7, max(2, len([m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]) + 2)),
                "tags": ["python", "class"]
            })
            edges.append({
                "source": file_id,
                "target": cls_id,
                "type": "contains",
                "weight": 1.0,
                "reason": f"{rel_path} defines class {cls.name}."
            })
            for b in cls.bases:
                base_name = b.id if isinstance(b, ast.Name) else (b.attr if isinstance(b, ast.Attribute) else None)
                if base_name == "BaseCommand":
                    edges.append({
                        "source": cls_id,
                        "target": "class:src/easy_tdx/commands/base.py:BaseCommand",
                        "type": "inherits",
                        "weight": 0.9,
                        "reason": f"{cls.name} inherits BaseCommand."
                    })
                elif base_name == "Strategy":
                    edges.append({
                        "source": cls_id,
                        "target": "class:src/easy_tdx/backtest/strategy.py:Strategy",
                        "type": "inherits",
                        "weight": 0.9,
                        "reason": f"{cls.name} inherits Strategy."
                    })
                elif base_name == "BaseIndicator":
                    edges.append({
                        "source": cls_id,
                        "target": "class:src/easy_tdx/indicator/base.py:BaseIndicator",
                        "type": "inherits",
                        "weight": 0.9,
                        "reason": f"{cls.name} inherits BaseIndicator."
                    })

        # Top-level functions
        for fn in tree.body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_id = f"function:{rel_path}:{fn.name}"
                fn_doc = (ast.get_docstring(fn) or "").replace("\n", " ").strip()
                fn_summary = fn_doc[:300] if fn_doc else f"Function {fn.name}() defined in {rel_path}."
                nodes.append({
                    "id": fn_id,
                    "type": "function",
                    "name": fn.name,
                    "filePath": rel_path,
                    "summary": fn_summary,
                    "complexity": 3,
                    "tags": ["python", "function"]
                })
                edges.append({
                    "source": file_id,
                    "target": fn_id,
                    "type": "contains",
                    "weight": 1.0,
                    "reason": f"{rel_path} defines function {fn.name}()."
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
            "complexity": {"min": 1, "max": 8, "avg": 3.0},
            "notes": f"Batch {batch_idx} analyzed via AST. {len(nodes)} nodes, {len(edges)} edges from {len(files)} files."
        }
    }
    out_path = f"{INTER}/batch-{batch_idx}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out_path


if __name__ == "__main__":
    idx = int(sys.argv[1])
    nodes, edges, files = analyze_batch(idx)
    out = write_batch(idx, nodes, edges, files)
    print(f"Wrote {out}: {len(nodes)} nodes, {len(edges)} edges")