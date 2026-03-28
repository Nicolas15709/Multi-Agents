# Multi-Agents

Workspace principal de Mission Control / Multi-Agents.

## Arranque rápido

### Dashboard (desde la raíz)
```bash
npm run dev
```

### Build del dashboard
```bash
npm run build
```

### Runtime Python
```bash
npm run runtime
```

### Exportar snapshot manual
```bash
npm run snapshot
```

## Nota importante
La implementación activa del proyecto vive en:
- `MissionControl/apps/dashboard`
- `MissionControl/runtime/python`

Los scripts de la raíz están alineados para ejecutar esas rutas directamente y evitar el flujo legacy que apuntaba a `src/main_orchestrator.js`.
