# Virtual Agency: Vercel + VPS

Usa esta arquitectura:

- `Vercel`: frontend React del dashboard
- `VPS`: runtime Python, API HTTP, WebSocket y OpenClaw
- `Nginx`: reverse proxy del VPS para `/api` y `/ws`

## Frontend en Vercel

Variables:

```env
VITE_MISSION_CONTROL_API_BASE_URL=https://runtime.tudominio.com/api
VITE_MISSION_CONTROL_WS_URL=wss://runtime.tudominio.com/ws
```

Archivo base:

[`apps/dashboard/.env.vercel.example`](/C:/Users/Nicolas/Documents/Multi-Agents/Multi-Agents/MissionControl/apps/dashboard/.env.vercel.example)

## Runtime en VPS

Archivo base:

[`MissionControl/.env.vps.example`](/C:/Users/Nicolas/Documents/Multi-Agents/Multi-Agents/MissionControl/.env.vps.example)

Valores importantes:

```env
MISSION_CONTROL_ENV=production
MISSION_CONTROL_RUNTIME_DB=/srv/virtual-agency/data/runtime.db
MISSION_CONTROL_WEBSOCKET=true
MISSION_CONTROL_WEBSOCKET_HOST=127.0.0.1
MISSION_CONTROL_WEBSOCKET_PORT=8765
MISSION_CONTROL_API=true
MISSION_CONTROL_API_HOST=127.0.0.1
MISSION_CONTROL_API_PORT=8787
MISSION_CONTROL_API_CORS_ORIGIN=https://tu-frontend.vercel.app
MISSION_CONTROL_JWT_SECRET=pon-un-secreto-largo
MISSION_CONTROL_DASHBOARD_USERNAME=admin
MISSION_CONTROL_DASHBOARD_PASSWORD=pon-una-clave-fuerte
```

## Nginx

Config base:

[`deployment/nginx.runtime-only.conf`](/C:/Users/Nicolas/Documents/Multi-Agents/Multi-Agents/MissionControl/deployment/nginx.runtime-only.conf)

Ese archivo expone:

- `https://runtime.tudominio.com/api` -> `127.0.0.1:8787`
- `wss://runtime.tudominio.com/ws` -> `127.0.0.1:8765`

## systemd

Servicio base:

[`systemd/virtual-agency.service`](/C:/Users/Nicolas/Documents/Multi-Agents/Multi-Agents/MissionControl/systemd/virtual-agency.service)

Comandos típicos:

```bash
sudo cp systemd/virtual-agency.service /etc/systemd/system/virtual-agency.service
sudo systemctl daemon-reload
sudo systemctl enable virtual-agency
sudo systemctl start virtual-agency
sudo systemctl status virtual-agency
```

## OpenClaw

OpenClaw puede vivir en el mismo VPS y mandar trabajo a:

- `POST /api/openclaw/intake`

## Si el dashboard sale disconnected

Revisa en este orden:

1. el runtime está corriendo
2. `https://runtime.tudominio.com/health` responde
3. hiciste login en el dashboard
4. el frontend apunta a `https://.../api` y `wss://.../ws`
