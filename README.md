# keeper-clean

Code-first rebuild of Keeper with a strict clean structure:

- `python/`: Python source scripts from `D:\Keeper-Clean-Loop1` and subfolders
- `core_rules/`: Canonical core rule + state files
- `core_runtime/`: Launchers and runtime requirements

## Explicit Exclusions

- `VM TESTRUN HOHE TIEFE` is fully excluded
- historical/documentary payload removed (`archive/`, `reports/`, `tasks/`, bulk docs)

## Structure

```text
keeper-clean/
  core_rules/
  core_runtime/
  python/
    root/
    scripts/
    tools/
    tests/
    ...
```
