# Virtual Agency Runtime (Python)

Este directorio contiene el runtime operativo de `Virtual Agency`.

## Stack
- Python
- SQLite
- WebSocket local
- HTTP API para snapshot, intake y approvals
- Catálogo de especialistas desde `agency-agents`

## Responsabilidades
- intake universal de problemas
- planner abierto por capacidades y dominios
- hiring dinámico de especialistas
- coordinación entre agentes con memoria compartida
- approvals para acciones sensibles
- budgets de autonomía y budgets por tipo de acción externa

## Comandos útiles
- Iniciar runtime persistente:
  - `python3 main.py`
- Enviar una misión nueva:
  - `python3 submit_mission.py "Titulo" "Objetivo" --mode general_operating_request --priority high --schedule manual:adhoc`
- Ver estado estructurado en JSON:
  - `python3 print_status.py`
- Ejecutar diagnóstico operativo legible o en JSON:
  - `python3 doctor.py`
  - `python3 doctor.py --json`
- Exportar snapshot puntual:
  - `python3 export_snapshot.py`

## Endpoints HTTP
- `GET /api/health`
- `GET /api/snapshot`
- `GET /api/intake/requests`
- `GET /api/agent-templates`
- `GET /api/missions/:missionId/hire-requests`
- `GET /api/missions/:missionId/hire-suggestions`
- `GET /api/missions/:missionId/approvals`
- `POST /api/missions`
- `POST /api/intake/requests`
- `POST /api/openclaw/intake`
- `POST /api/missions/:missionId/hire-subagent`
- `POST /api/hire-requests/:hireRequestId/approve`
- `POST /api/action-approvals/:approvalId/approve`
- `POST /api/action-approvals/:approvalId/reject`

## Intake para móvil / OpenClaw

Ejemplo:

```json
POST /api/openclaw/intake
{
  "title": "Login roto en movil",
  "message": "Usuarios no pueden iniciar sesion desde Safari iPhone",
  "priority": "high",
  "requested_by": "Nicolas",
  "auto_dispatch": true
}
```

Eso crea una solicitud persistente y, si `auto_dispatch` está activa, la convierte en misión con planner abierto.

## Hiring dinámico por misión

Puedes contratar subagentes temporales por misión. El runtime:

- crea el agente dinámico
- lo marca como `mission_hire`
- lo ata a la misión
- le crea una tarea propia
- actualiza review y closeout para esperar su entrega

También puede apoyarse en el catálogo de `agency-agents` usando `MISSION_CONTROL_SPECIALIST_TEMPLATES_ROOT`.

Ejemplo:

```json
POST /api/missions/mission-123/hire-subagent
{
  "template_id": "marketing-social-media-strategist",
  "display_name": "Social Media Strategist",
  "role": "social-media-strategist",
  "personality": "Cross-platform strategist with strong B2B social instincts",
  "capabilities": "linkedin, campaigns, thought-leadership",
  "notes": "Own launch messaging and executive social presence",
  "budget_monthly_cents": 0
}
```

Si `MISSION_CONTROL_HIRE_APPROVALS=true`, el hire queda `pending` hasta aprobación:

```json
POST /api/hire-requests/hire-123/approve
{
  "create_task": true
}
```

## Guardrails de autonomía y gasto

Cada misión recibe un presupuesto autónomo persistente:

- `MISSION_CONTROL_MAX_AUTONOMOUS_STEPS`
- `MISSION_CONTROL_MAX_ESTIMATED_TOKENS`
- `MISSION_CONTROL_MAX_RUNTIME_TICKS`
- `MISSION_CONTROL_MAX_DYNAMIC_HIRES`
- `MISSION_CONTROL_ACTION_BUDGETS_JSON`

Si supera el límite, la misión pasa a `needs_human` y queda marcada como `exhausted`.

Las tareas con `external_action_kind` pueden:

- abrir una solicitud de aprobación por acción
- consumir presupuesto específico por tipo de acción (`outreach`, `publish`, `legal_release`, `financial_commitment`)
- quedar bloqueadas hasta aprobación humana si su `approval_policy` lo exige

## Coordinación entre agentes

El runtime ahora persiste coordinación ligera:

- `sharedMemory`: memoria compartida de misión con resúmenes por workstream
- `agentMessages`: handoffs dependientes entre agentes y tareas
- `actionApprovals`: cola de aprobaciones para acciones sensibles

Cuando una tarea termina, deja un resumen en memoria compartida y envía handoffs a las tareas dependientes. Cuando la tarea siguiente arranca, consume ese contexto.

## Seguridad mínima de API

Si defines `MISSION_CONTROL_API_AUTH_TOKEN`, toda la API excepto `/health` requerirá:

- `Authorization: Bearer <token>`

o alternativamente:

- `X-Mission-Control-Token: <token>`
