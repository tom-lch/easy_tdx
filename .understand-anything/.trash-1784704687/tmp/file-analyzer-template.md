# File Analyzer Agent Prompt — TEMPLATE (DO NOT MODIFY)

You are analyzing a single batch of files for the `easy-tdx` project. Your output is a single JSON file at the path specified by `OUTPUT_PATH` below.

## ABSOLUTE REQUIREMENTS

1. **Output is a single JSON file** at the path in `OUTPUT_PATH`. Nothing else.
2. **Top-level keys MUST be exactly**: `schemaVersion`, `batchIndex`, `projectRoot`, `filesAnalyzed`, `nodes`, `edges`, `summary`
3. **`schemaVersion`** = `1`
4. **`batchIndex`** = the integer from `BATCH_INDEX` below
5. **`projectRoot`** = the absolute path from `PROJECT_ROOT` below
6. **`filesAnalyzed`** = array of `{path, language, sizeLines, fileCategory}` — copy EXACTLY from the file list in `BATCH_FILES` below
7. **`nodes`** = array of node objects (see Node Schema below)
8. **`edges`** = array of edge objects (see Edge Schema below)
9. **`summary`** = object with `nodesCreated`, `edgesCreated`, optional `notes`

## Node Schema (each object in `nodes`)

```json
{
  "id": "<prefix>:<identifier>",
  "type": "<file|function|class|module|concept|config|document|service|table|endpoint|pipeline|schema|resource>",
  "name": "<short display name>",
  "filePath": "<relative path from PROJECT_ROOT>",
  "summary": "<1-3 sentence description of what this node IS and DOES>",
  "complexity": <integer 1-10, or "simple"|"moderate"|"complex">,
  "tags": ["<keyword>", ...],
  "languageNotes": "<optional: language-specific notes>",
  "languageLesson": "<optional: teaching insight>"
}
```

**ID prefixes (mandatory)** — see `/Users/lichao/work/jytx/easy_tdx/.understand-anything/intermediate/batch-1.json` for examples.

## Edge Schema (each object in `edges`)

```json
{
  "source": "<node-id>",
  "target": "<node-id>",
  "type": "<imports|calls|exports|contains|inherits|implements|configures|depends_on|tested_by|documents|deploys|serves|provisions|triggers|reads_from|writes_to|transforms|validates|related|similar_to|migrates|routes|defines_schema>",
  "weight": <0.0-1.0>,
  "reason": "<1 sentence explaining WHY this edge exists>"
}
```

Use `weight=0.7` for `imports`, `weight=0.8` for `calls`/`exports`, `weight=1.0` for `contains`. Default `0.5`.

## CRITICAL RULES

1. **Every file in BATCH_FILES MUST produce at least one node.** If a file is trivial, emit one file-level node.
2. **Python files**: emit a `file:<path>` node PLUS a node for each top-level class/function defined in the file. Use IDs like `class:<path>:<ClassName>` and `function:<path>:<func_name>`.
3. **YAML/Markdown/JSON/HTML files**: emit one node per file (type `pipeline`/`document`/`config`/`document` respectively).
4. **Edges**: emit at minimum `contains` edges from each file node to its children (classes/functions). For Python files, emit `imports` edges from the file to imported project modules (use `IMPORT_MAP` if provided).
5. **Do NOT invent files.** Only reference files you've actually read.
6. **Do NOT use "description" instead of "reason"** for edges. The merge script and dashboard require `reason`.

## YOUR SPECIFIC TASK

- **PROJECT_ROOT**: `REPLACE_PROJECT_ROOT`
- **BATCH_INDEX**: `REPLACE_BATCH_INDEX`
- **OUTPUT_PATH**: `REPLACE_OUTPUT_PATH`
- **LANGUAGE_DIRECTIVE**: `REPLACE_LANGUAGE`
- **BATCH_FILES**: (exact files to analyze — read each one)
  ```
  REPLACE_BATCH_FILES
  ```
- **PRE_RESOLVED_IMPORTS** (empty `[]` if none): for each file in BATCH_FILES, an array of project-internal modules it imports.
- **NEIGHBOR_MAP** (empty if none): cross-batch neighbor files with their exported symbols.

## STEPS

1. Read `/Users/lichao/work/jytx/easy_tdx/.understand-anything/intermediate/batches.json` to confirm the file list for your batchIndex.
2. For each file in BATCH_FILES:
   a. Read the file (use offset/limit if very large).
   b. Decide node type and ID.
   c. Identify top-level classes/functions (Python), exports (TS), jobs (YAML), sections (MD).
3. Build the `nodes` and `edges` arrays.
4. Validate: every file → at least one node, all edges have required fields, all IDs follow the prefix convention.
5. Write the JSON file at OUTPUT_PATH using `write_file`. Top-level structure is EXACTLY as specified above.
6. Return a one-paragraph summary of what you produced.

## DO NOT

- Do not write to any path other than OUTPUT_PATH.
- Do not run the merge script, do not modify scan-result.json, do not touch other batch-*.json files.
- Do not include prose outside the JSON file (except your final return message).
- Do not skip files. Every file in BATCH_FILES gets at least one node.