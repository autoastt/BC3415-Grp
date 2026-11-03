## Summary

<!-- 1 to 3 sentences: what this pull request does and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Breaking change (explain under "Deployment notes")

## What changed

<!-- Group changes by area and name the main files. Delete sections you don't need. -->

### Backend
-

### Frontend
-

### Documentation
-

## How to test

```bash
cd backend
pytest -q
```

<!-- Manual steps a reviewer can follow: the exact chat messages to send and what should happen. -->
1.

## Test results

- Offline suite (`pytest -q`): <!-- e.g. 99 passed -->
- Frontend build (`npm run build`): <!-- passed / not run -->
- Live evaluation (`python -m tests.eval_behavior`): <!-- e.g. 23/23 / not run -->

## Deployment notes

<!-- New dependencies, environment variables, data changes, or anything to do before or after merging. Write "None" if nothing. -->

## Contributors

<!-- Who worked on this and what each person did. Helps show the group's division of work. -->
-

## Checklist

- [ ] Tests added or updated, and `pytest -q` passes
- [ ] Frontend builds (`npm run build`)
- [ ] README or docs updated if behaviour changed
- [ ] No secrets committed (`.env`, API keys, the `data/` folder)
- [ ] Someone else has reviewed this pull request

## Screenshots

<!-- Optional: UI changes, chat replies, admin views. -->
