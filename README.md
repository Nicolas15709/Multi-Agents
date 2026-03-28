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

### Flujo base
1. Supervisor planifica
2. Researcher investiga
3. Designer define prototipo, UX/UI y stack visual recomendado
4. Developer implementa
5. QA revisa
6. Security templates y hardening pueden agregar ciclos adicionales según la misión

## Núcleo + modos

El sistema no crecerá inicialmente añadiendo demasiados agentes. En su lugar:
- mantiene un núcleo fijo de 5 agentes
- usa modos y plantillas de misión
- adapta prioridades, entregables y peso de cada agente según el trabajo

## Plantillas de misión

Mission Control incluirá plantillas amplias y completas, además de misiones libres.

### Desarrollo / producto
- software_build
- prototype_to_build
- landing_launch
- feature_extension
- bugfix_debug
- documentation_pack

### Seguridad / calidad
- security_review
- qa_hardening
- post_build_audit

### Marketing / marca
- marketing_campaign
- brand_growth
- content_engine
- social_presence_audit

### Negocio / prospección
- business_audit_proposal
- competitor_intelligence
- offer_design

### Investigación / operación
- research_only
- monitor_and_report
- launch_mode
- maintenance_cycle

## Agenda interna avanzada

Mission Control incorpora una capa de agenda autónoma avanzada:
- backlog
- prioridades
- tareas programadas
- dependencias
- ventanas horarias
- objetivos recurrentes
- planificación futura
- cooldowns
- memoria de trabajo
- próximos pasos
- prevención de loops absurdos

## Prioridades e interrupciones

Si entra una misión nueva mientras otra está en curso, el sistema debe:
- comparar prioridad
- evaluar impacto
- decidir si ejecutar, encolar, diferir o consultar

### Política
- resolución mixta
- auto-decide en casos claros
- consulta al usuario por Telegram en casos ambiguos o sensibles

## Acciones externas y permisos

### Política general
- externas controladas
- no globales
- se habilitan por política explícita

### Granularidad
Permisos por:
- integración
- cuenta/recurso
- acción

### Modos posibles
- prohibido
- automático permitido
- permitido con condiciones
- aprobación puntual

## Políticas, secretos y artifacts

### Políticas
- modelo híbrido
- Supabase como configuración central
- runtime con caché local aplicada

### Secretos
- modelo híbrido
- metadata/configuración en backend de producto
- secretos reales en entorno seguro del runtime
- nunca expuestos al frontend

### Artifacts
- modelo híbrido
- local para temporales/intermedios/pesados
- Supabase Storage para artifacts importantes/finales/compartibles

## Roles y acceso

### Login
- siempre primero
- Supabase Auth con Magic Link

### Roles iniciales
#### Admin
- control total
- permisos
- misiones
- integraciones
- configuración
- políticas
- aprobación de acciones

#### Viewer / read-only
- ve dashboard
- ve agentes, eventos, mission room y artifacts visibles
- no cambia nada sensible

## Telegram vs Dashboard

### Telegram
Se usará para:
- notificaciones
- alertas
- decisiones rápidas
- conflictos de prioridad
- aprobaciones pendientes
- bloqueos
- retries agotados
- misión completada
- aviso de resumen disponible

### Dashboard
Se usará para:
- resúmenes completos
- historial
- análisis
- cards de agentes
- inspector
- mission room
- artifacts
- agenda y trabajo futuro

## Dashboard

### Primera pantalla
- login

### Entrada principal
- command center general
- acceso a misión activa

### Dentro de una misión
- escena visual isométrica / 2.5D
- agentes como personajes con movimiento y actividad en tiempo real
- cards de agentes
- feed de eventos
- inspector del agente
- panel de misión
- timeline
- artifacts

### Estilo visual
- híbrido: tecnológico + cálido
- amigable
- premium
- con personalidad
- no corporativo frío

### Agent cards
Cada agente tendrá card con:
- avatar acorde al personaje
- nombre
- rol
- personalidad breve
- estado actual
- tarea activa
- trabajo reciente
- artifacts recientes
- historial diario útil
- nivel de actividad
- bloqueo o salud operativa

## Visibilidad del trabajo interno

### Política
Equilibrada y filtrada.

### Se muestra
- estados
- acciones
- handoffs
- decisiones resumidas
- artifacts
- bloqueos
- retries
- progreso

### No se muestra crudo
- reasoning interno completo
- prompts sensibles
- secretos
- ruido excesivo
- contexto bruto innecesario

## Creación de misiones

Ambos:
- formulario simple
- wizard guiado

## Misiones programadas

- manuales + programadas
- soporte para seguimiento continuo, monitoreo, mantenimiento y campañas recurrentes

## Horario operativo

Mixto:
- ciertas tareas 24/7
- otras con ventanas horarias
- configurable según prioridad, misión, integración o política

## Integraciones prioritarias v1
- Telegram
- Web search / fetch
- GitHub
- Google Maps / negocio local
- Instagram research / análisis

## MVP

### Prioridad
Equilibrado:
- runtime real
- agenda real
- seguridad real
- dashboard ya atractivo y vivo

## Estructura del proyecto

```text
MissionControl/
├── README.md
├── package.json
├── .env.example
├── .gitignore
├── docs/
│   ├── MASTER_PLAN.md
│   ├── SECURITY_MODEL.md
│   ├── PRODUCT_REQUIREMENTS.md
│   ├── AGENTS_OVERVIEW.md
│   └── TEMPLATES.md
├── config/
│   ├── agents.json
│   ├── orchestrator.json
│   ├── mission-templates.json
│   ├── project.decisions.json
│   └── docker.future.json
├── apps/
│   └── dashboard/
│       ├── README.md
│       └── src/
│           └── placeholder.md
├── prompts/
│   ├── supervisor.AGENTS.md
│   ├── researcher.AGENTS.md
│   ├── designer.AGENTS.md
│   ├── developer.AGENTS.md
│   └── qa.AGENTS.md
├── runtime/
│   ├── python/
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── planner.py
│   │   ├── policies.py
│   │   ├── notifications.py
│   │   ├── websocket_server.py
│   │   └── templates.py
│   └── node-legacy/
│       └── README.md
├── src/
│   ├── legacy/
│   │   ├── agents.js
│   │   ├── context.js
│   │   ├── db.js
│   │   ├── logger.js
│   │   ├── main_orchestrator.js
│   │   ├── retry.js
│   │   ├── schema.sql
│   │   ├── supabase.js
│   │   └── workflow.js
├── supabase/
│   ├── schema.sql
│   └── policies.sql
├── data/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
└── systemd/
    └── mission-control.service
```

## Próximos pasos

1. Consolidar runtime Python + LangGraph
2. Definir dashboard Vite + React con login-first
3. Conectar Supabase Auth, roles y políticas
4. Implementar planner, agenda avanzada y scheduling
5. Implementar event stream por WebSocket local
6. Diseñar cards, mission room y command center
7. Añadir catálogo completo de plantillas
8. Preparar futura dockerización por agente
