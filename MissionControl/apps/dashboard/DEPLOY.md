# Dashboard — Deployment Guide

The dashboard is a static Vite/React app. It can be deployed to **Vercel** or **Cloudflare Pages**. The Python backend runs on a separate VPS and is referenced only through environment variables — no backend code is bundled with the frontend.

---

## Environment Variables

These must be set in the Vercel / Cloudflare Pages dashboard **before** triggering a build. The values are baked into the static bundle at build time by Vite.

| Variable | Description | Example |
|---|---|---|
| `VITE_MISSION_CONTROL_API_BASE_URL` | Full HTTPS URL of the backend REST API — **no trailing slash** | `https://api.tu-dominio.com/api` |
| `VITE_MISSION_CONTROL_WS_URL` | Full WSS URL of the backend WebSocket endpoint | `wss://api.tu-dominio.com/ws` |

> If these variables are not set, the app falls back to `127.0.0.1:8787` (API) and `127.0.0.1:8765` (WS) when running on a Vite dev/preview port (4173, 5173, 5174), and to relative `/api` + `/ws` paths otherwise.

---

## Option A — Deploy on Vercel

### 1. Import the repository

1. Go to <https://vercel.com/new> and click **Import Git Repository**.
2. Select the `Multi-Agents` repo (grant access if prompted).
3. Set the **Root Directory** to `MissionControl/apps/dashboard`.
   Vercel will detect the `vercel.json` at that path and use it automatically.

### 2. Configure environment variables

In the Vercel project settings → **Environment Variables**, add:

```
VITE_MISSION_CONTROL_API_BASE_URL = https://api.tu-dominio.com/api
VITE_MISSION_CONTROL_WS_URL       = wss://api.tu-dominio.com/ws
```

Set the scope to **Production** (and optionally **Preview** with staging values).

### 3. Deploy

Click **Deploy**. Vercel runs `npm run build`, outputs to `dist/`, and serves SPA routing via the `rewrites` rule in `vercel.json`.

### 4. Subsequent deploys

Every push to `main` triggers an automatic redeploy. To redeploy manually, go to **Deployments** → **Redeploy**.

---

## Option B — Deploy on Cloudflare Pages

### 1. Create a Pages project

1. Go to <https://dash.cloudflare.com/> → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**.
2. Select the `Multi-Agents` repo.
3. Set **Root directory** to `MissionControl/apps/dashboard`.

### 2. Configure the build

| Setting | Value |
|---|---|
| Framework preset | `Vite` |
| Build command | `npm run build` |
| Build output directory | `dist` |

### 3. Configure environment variables

Under **Settings** → **Environment variables**, add:

```
VITE_MISSION_CONTROL_API_BASE_URL = https://api.tu-dominio.com/api
VITE_MISSION_CONTROL_WS_URL       = wss://api.tu-dominio.com/ws
```

Set them for the **Production** environment.

### 4. SPA routing

The `public/_redirects` file (`/* /index.html 200`) is copied into `dist/` by Vite and tells Cloudflare Pages to serve `index.html` for all routes — no extra configuration needed.

### 5. Deploy

Click **Save and Deploy**. Every push to `main` triggers an automatic redeploy.

---

## Updating the Backend URL

If the VPS address or domain changes:

**Vercel:** Project → Settings → Environment Variables → edit the two `VITE_*` vars → **Save** → go to Deployments → **Redeploy** (select the latest deployment, check "Use existing Build Cache" only if the URLs didn't change in code).

**Cloudflare Pages:** Project → Settings → Environment variables → edit → **Save** → trigger a new deploy via a git push or the **Retry deployment** button.

> Because the URLs are inlined at build time, you must trigger a new build after changing them. A simple cache-invalidation redeploy is not sufficient — the build must run again.

---

## Local Development

```bash
cd MissionControl/apps/dashboard
npm install
npm run dev          # uses .env.development → 127.0.0.1:8787 / 8765
```

To preview the production build locally before deploying:

```bash
npm run build        # or npm run build:production
npm run preview      # serves dist/ on port 4173
```
