# Deployment: Railway Native GitHub Integration

## Summary

Railway has a built-in GitHub App integration that auto-deploys on push. No GitHub Actions workflow is needed. The mechanism is: push → GitHub webhook → Railway fetches code → builds → deploys.

This is configured per service in the Railway dashboard. There is no YAML file, no CI pipeline to write.

## How It Works

1. You connect a GitHub repo to a Railway service in the dashboard
2. Railway installs a GitHub App on the repo (one-time OAuth flow)
3. Every push to the configured branch triggers a build for connected services
4. Each service can have its own **root directory** and **watch paths** to scope what triggers it

## Monorepo Configuration

This project is a monorepo with `backend/`, `frontend/`, and `martin/` directories. Railway supports this natively.

### Per-Service Settings (all set in Railway dashboard → Service Settings)

| Service | Root Directory | Watch Paths | Source Type | Notes |
|---------|---------------|-------------|-------------|-------|
| backend | `/backend` | `backend/**` | GitHub repo | Builds from `backend/Dockerfile` |
| frontend | `/frontend` | `frontend/**` | GitHub repo | Builds from `frontend/Dockerfile` |
| martin | — | — | Docker image | `ghcr.io/maplibre/martin:v0.15.0`. No source build. Not connected to GitHub. |
| PostGIS | — | — | Template | Database. No deploys. Not connected to GitHub. |

### Root Directory

- Set in **Service Settings → Root Directory**
- This is a **dashboard-only setting** — it cannot be set via `railway.toml` or any config file
- When set to `/backend`, Railway builds as if `/backend` is the project root (finds `Dockerfile` there)

### Watch Paths

- Set in **Service Settings → Watch Paths** (dashboard UI)
- Gitignore-style patterns, one per line
- Patterns match from **repo root**, even when a root directory is set
- Example: `backend/**` means "only rebuild this service when files under `backend/` change"
- **Known issue (confirmed by Railway staff, March 2026):** `watchPatterns` in `railway.toml` is silently ignored when Railpack (the new default builder) is active. Dashboard-configured watch paths work correctly.

## What Does NOT Need to Change

- **Database (PostGIS):** Never touched by deploys. Data persists on a Railway volume across all service restarts and redeployments.
- **Martin:** Runs from a pre-built Docker image. No source code to deploy. Only needs a redeploy if new PostGIS tables are added (which only happens if the ingestion pipeline is re-run).
- **Environment variables:** Already set on each service. Persist across deploys.

## `railway up` vs GitHub Deploys

- `railway up` uploads local files directly to Railway
- GitHub-connected deploys pull from GitHub on push
- They are not mutually exclusive — you can `railway up` to a service that also has a GitHub connection
- Most recent deploy wins
- Connecting a repo to an existing CLI-deployed service triggers an immediate deploy from the latest commit

## Manual Steps to Enable

### Prerequisites
- Repo must be pushed to GitHub

### Steps (all in Railway dashboard)

1. **For the `backend` service:**
   - Service Settings → Service Source → Connect Repo
   - Select the GitHub repo and `main` branch
   - Set Root Directory: `/backend`
   - Set Watch Paths: `backend/**`

2. **For the `frontend` service:**
   - Service Settings → Service Source → Connect Repo
   - Select the GitHub repo and `main` branch
   - Set Root Directory: `/frontend`
   - Set Watch Paths: `frontend/**`

3. **Martin and PostGIS:** Leave as-is. No changes.

### Optional: "Wait for CI"
Railway has a "Wait for CI" toggle per service. When enabled, Railway pauses in a `WAITING` state until a GitHub Actions check passes before deploying. This is the only scenario where GitHub Actions would be involved — and it's entirely optional. For a demo project, this adds complexity with no benefit.

## Risk Assessment

- **Connecting a repo triggers an immediate deploy.** The code on GitHub is identical to what was deployed via `railway up`, so the build output should be identical. The running service continues until the new build succeeds. If the build fails, the old deployment stays live.
- **Root directory misconfiguration** is the main risk. If set wrong, Railway won't find the Dockerfile and the build fails. This is reversible — fix the setting and redeploy.
- **Database is never affected** by any deploy operation.

## Recommendation

Do this after the demo, not before. The app is live and working. This is a 5-minute dashboard task with low risk, but there is no reason to touch a working deployment before a demo.

## Sources

- [Railway: Controlling GitHub Autodeploys](https://docs.railway.com/guides/github-autodeploys)
- [Railway: Deploying a Monorepo](https://docs.railway.com/guides/monorepo)
- [Railway: Build Configuration](https://docs.railway.com/builds/build-configuration)
- [Railway: Config as Code](https://docs.railway.com/reference/config-as-code)
- [Railway Help Station: Watch paths ignored with Railpack](https://station.railway.com/questions/watch-paths-are-ignored-82e84cb5)
