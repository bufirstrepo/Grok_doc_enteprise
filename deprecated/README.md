# Deprecated Files

This directory contains files that have been identified as "zombie" files - Python files in `src/` that are not imported by any of the main entrypoints (`app.py`, `local_inference.py`, `src/core/router.py`).

## Files Moved Here

### migrate_config.py
- **Original location**: `src/config/migrate_config.py`
- **Reason**: Not imported by any other file in the codebase
- **Date moved**: 2025-12-01
- **Status**: Awaiting human review before permanent deletion

## Why These Files Were Moved

These files were identified through static import graph analysis during the production sanitization process. The analysis traced all imports from the main entrypoints and flagged files that are not part of the active import tree.

## Before Deleting

Please manually verify:
1. The file is not dynamically imported (e.g., via `importlib`)
2. The file is not used by external tools or scripts
3. The file is not referenced in configuration files

## To Restore a File

If a file was moved here incorrectly, simply move it back to its original location:
```bash
mv deprecated/filename.py src/original/path/filename.py
```
