# Repository Maintenance Guide

This project is maintained as a private fork with regular upstream sync.

## Remote Layout

- `origin`: your private repository
- `upstream`: the original open-source repository

Example:

```bash
git remote add origin git@git.zzl6.cn:zzl/stock_prediction.git
git remote add upstream https://github.com/ZhuLinsen/daily_stock_analysis.git
```

## Branch Strategy

- `main`: stable branch for deployment
- `codex/feature-*`: feature branches for your custom work
- `codex/sync-upstream-*`: temporary branches for upstream merge

## Recommended Sync Cycle

Run this every 1-2 weeks:

```bash
./scripts/sync_upstream.sh main main
```

What it does:

1. fetch `origin` and `upstream`
2. fast-forward local `main`
3. create a sync branch
4. merge `upstream/main`
5. push the sync branch to `origin`

Then create a PR from `codex/sync-upstream-*` into `main`, run tests, and merge.

## Conflict Resolution Rules

1. keep upstream changes by default
2. re-apply your custom behavior in extension modules
3. avoid deep edits in core files unless necessary
4. document intentional deviations in PR description

## Custom Code Isolation

To reduce future conflicts, put custom logic in separate modules and call it via configuration switches.

Suggested folders:

- `src/extensions/`
- `api/v1/endpoints/custom_*.py`
- `docs/custom/`

## Merge Checklist

- run syntax check
- run key API smoke tests
- verify Docker build and container health check
- verify one real stock analysis flow end to end
