#!/usr/bin/env python3
"""Build a single file-analyzer dispatch prompt for one batch index."""

import json
import sys
from pathlib import Path

ROOT = Path("/Users/lichao/work/jytx/easy_tdx")
BATCHES = json.load(open(ROOT / ".understand-anything/intermediate/batches.json"))
TEMPLATE = (Path("/Users/lichao/work/jytx/easy_tdx/.understand-anything/tmp/file-analyzer-template.md")).read_text()


def build(batch_index: int) -> str:
    batch = BATCHES["batches"][batch_index]
    files = batch["files"]
    files_text = "\n".join(
        f'  - {f["path"]} ({f["language"]}, {f["fileCategory"]}, {f["sizeLines"]} lines)'
        for f in files
    )
    imports = batch.get("batchImportData", {})
    neighbors = batch.get("neighborMap", {})
    return (
        TEMPLATE
        .replace("REPLACE_PROJECT_ROOT", str(ROOT))
        .replace("REPLACE_BATCH_INDEX", str(batch_index))
        .replace(
            "REPLACE_OUTPUT_PATH",
            str(ROOT / f".understand-anything/intermediate/batch-{batch_index}.json"),
        )
        .replace("REPLACE_LANGUAGE", "English (en). Keep all technical terms in English.")
        .replace("REPLACE_BATCH_FILES", files_text)
        + "\n\n## PRE-RESOLVED IMPORTS (use directly, do NOT re-resolve from source)\n\n"
        + "```json\n"
        + json.dumps(imports, indent=2)
        + "\n```\n\n## CROSS-BATCH NEIGHBORS (with exported symbols)\n\n"
        + "```json\n"
        + json.dumps(neighbors, indent=2)
        + "\n```\n"
    )


if __name__ == "__main__":
    idx = int(sys.argv[1])
    sys.stdout.write(build(idx))