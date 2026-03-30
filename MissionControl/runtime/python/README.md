# Mission Control Runtime (Python)

Este directorio será el runtime principal del orquestador.

## Stack previsto
- Python
- LangGraph
- SQLite
- WebSocket local
- integración futura con Supabase

## Responsabilidades
- planificación
- agenda interna avanzada
- ejecución multiagente
- manejo de políticas
- persistencia operativa
- notificaciones
- streaming de eventos al dashboard

## Estado
Scaffold funcional en evolución.

## Comandos útiles
- Iniciar runtime persistente:
  - `python3 main.py`
- Enviar una misión nueva:
  - `python3 submit_mission.py "Título" "Objetivo" --mode software_build --priority high --schedule manual:adhoc`
- Ver estado estructurado en JSON:
  - `python3 print_status.py`
- Ejecutar diagnóstico operativo legible o en JSON:
  - `python3 doctor.py`
  - `python3 doctor.py --json`
- Asegurar un ciclo de mantenimiento recurrente (cron-friendly, con deduplicación):
  - `python3 ensure_maintenance_cycle.py --min-interval-hours 24 --schedule-label cron:daily`
- Exportar snapshot puntual:
  - `python3 export_snapshot.py`
