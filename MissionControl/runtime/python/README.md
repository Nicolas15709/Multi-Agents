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
  - `python3 submit_mission.py "Título" "Objetivo" --mode software_build --priority high`
- Exportar snapshot puntual:
  - `python3 export_snapshot.py`
