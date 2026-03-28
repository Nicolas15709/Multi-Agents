# Mission Control

Mission Control es una plataforma multiagente autónoma con dashboard visual, pensada para coordinar desarrollo, marketing, auditoría digital, investigación, seguridad defensiva y ejecución híbrida con una experiencia tipo centro de operaciones.

## Visión

Mission Control no será solo un chat. Será un centro de operaciones donde un equipo de agentes especializados trabaja con autonomía, agenda propia, prioridades, memoria operativa y reglas de seguridad, mientras el usuario supervisa desde un dashboard visual tipo videojuego.

## Objetivo principal

Permitir que un equipo de agentes:
- reciba misiones
- las descomponga
- investigue
- diseñe
- construya
- revise
- endurezca seguridad
- mantenga trabajo continuo
- y solo escale al usuario cuando realmente haga falta

## Arquitectura general

### Frontend
- Vite + React
- desplegado en Vercel
- login primero
- dashboard visual híbrido, cálido + tecnológico
- estilo isométrico / 2.5D ilustrado
- animaciones ligeras en tiempo real
- cards de agentes, inspector, feed, mission room

### Backend de producto
- Supabase
- auth
- perfiles
- roles
- misiones
- eventos persistidos
- preferencias
- permisos/políticas
- artifacts importantes
- storage final

### Runtime de ejecución
- Python
- LangGraph
- self-hosted orchestrator
- SQLite al inicio para estado interno
- WebSocket local para tiempo real
- preparado para migrar a hardware más potente en el futuro
- preparado para Docker por agente más adelante

## Seguridad

Mission Control sigue un enfoque security-first.

### Reglas base
- login siempre primero
- nada de secretos en código
- nada de tokens expuestos al frontend
- todo secreto sensible en variables de entorno o capa segura
- separación estricta entre frontend, backend de producto y runtime
- validación fuerte de inputs
- mínimo privilegio
- RLS en Supabase
- logs sin secretos
- permisos granulares por integración, cuenta/recurso y acción
- fuera de política explícita, no se ejecuta
- arquitectura portable y migrable
- autonomía alta con guardrails

## Equipo base

Mission Control mantiene un núcleo fijo de 5 agentes:

1. Supervisor
2. Researcher
3. Designer / Prototype Architect
4. Developer
5. QA
