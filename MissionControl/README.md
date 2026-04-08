# Virtual Agency

Virtual Agency es una plataforma multiagente autÃ³noma con dashboard visual, pensada para coordinar desarrollo, marketing, auditorÃ­a digital, investigaciÃ³n, seguridad defensiva y ejecuciÃ³n hÃ­brida con una experiencia tipo centro de operaciones.

## VisiÃ³n

Virtual Agency no serÃ¡ solo un chat. SerÃ¡ un centro de operaciones donde un equipo de agentes especializados trabaja con autonomÃ­a, agenda propia, prioridades, memoria operativa y reglas de seguridad, mientras el usuario supervisa desde un dashboard visual tipo videojuego.

## Objetivo principal

Permitir que un equipo de agentes:
- reciba misiones
- las descomponga
- investigue
- diseÃ±e
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
- dashboard visual hÃ­brido, cÃ¡lido + tecnolÃ³gico
- estilo isomÃ©trico / 2.5D ilustrado
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
- permisos/polÃ­ticas
- artifacts importantes
- storage final

### Sistema de Memoria (Vector + SesiÃ³n)
- **Memoria Vectorial**: Supabase pgvector para bÃºsqueda semÃ¡ntica a largo plazo (experiencias, eventos, artifacts)
- **Memoria por SesiÃ³n**: SQLite local con state diffing y snapshots comprimidos (estado en tiempo real)
- **Embeddings**: OpenAI o Groq (text-embedding-ada-002)
- **TTL automÃ¡tico**: PolÃ­ticas configurables de retenciÃ³n y limpieza
- **Sync**: Cola de sincronizaciÃ³n para consistencia eventual

> Consulta `MEMORY.md` para la guÃ­a completa de configuraciÃ³n, API y operaciÃ³n.

### Runtime de ejecuciÃ³n
- Python
- LangGraph
- self-hosted orchestrator
- SQLite al inicio para estado interno
- WebSocket local para tiempo real
- preparado para migrar a hardware mÃ¡s potente en el futuro
- preparado para Docker por agente mÃ¡s adelante

## Despliegue recomendado

- `Vercel` para el dashboard frontend
- `VPS` para runtime Python, API, WebSocket y OpenClaw
- `Nginx` en el VPS como reverse proxy para `/api` y `/ws`

Guia:

[`deployment/VERCEL_VPS.md`](/C:/Users/Nicolas/Documents/Multi-Agents/Multi-Agents/MissionControl/deployment/VERCEL_VPS.md)

## Seguridad

Virtual Agency sigue un enfoque security-first.

### Reglas base
- login siempre primero
- nada de secretos en cÃ³digo
- nada de tokens expuestos al frontend
- todo secreto sensible en variables de entorno o capa segura
- separaciÃ³n estricta entre frontend, backend de producto y runtime
- validaciÃ³n fuerte de inputs
- mÃ­nimo privilegio
- RLS en Supabase
- logs sin secretos
- permisos granulares por integraciÃ³n, cuenta/recurso y acciÃ³n
- fuera de polÃ­tica explÃ­cita, no se ejecuta
- arquitectura portable y migrable
- autonomÃ­a alta con guardrails

## Equipo base

Virtual Agency mantiene un nÃºcleo fijo de 5 agentes:

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
6. Security templates y hardening pueden agregar ciclos adicionales segÃºn la misiÃ³n

## NÃºcleo + modos

El sistema no crecerÃ¡ inicialmente aÃ±adiendo demasiados agentes. En su lugar:
- mantiene un nÃºcleo fijo de 5 agentes
- usa modos y plantillas de misiÃ³n
- adapta prioridades, entregables y peso de cada agente segÃºn el trabajo

## Plantillas de misiÃ³n

Virtual Agency incluirÃ¡ plantillas amplias y completas, ademÃ¡s de misiones libres.

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

### Negocio / prospecciÃ³n
- business_audit_proposal
- competitor_intelligence
- offer_design

### InvestigaciÃ³n / operaciÃ³n
- research_only
- monitor_and_report
- launch_mode
- maintenance_cycle

## Agenda interna avanzada

Virtual Agency incorpora una capa de agenda autÃ³noma avanzada:
- backlog
- prioridades
- tareas programadas
- dependencias
- ventanas horarias
- objetivos recurrentes
- planificaciÃ³n futura
- cooldowns
- memoria de trabajo
- prÃ³ximos pasos
- prevenciÃ³n de loops absurdos

## Prioridades e interrupciones

Si entra una misiÃ³n nueva mientras otra estÃ¡ en curso, el sistema debe:
- comparar prioridad
- evaluar impacto
- decidir si ejecutar, encolar, diferir o consultar

### PolÃ­tica
- resoluciÃ³n mixta
- auto-decide en casos claros
- consulta al usuario por Telegram en casos ambiguos o sensibles

## Acciones externas y permisos

### PolÃ­tica general
- externas controladas
- no globales
- se habilitan por polÃ­tica explÃ­cita

### Granularidad
Permisos por:
- integraciÃ³n
- cuenta/recurso
- acciÃ³n

### Modos posibles
- prohibido
- automÃ¡tico permitido
- permitido con condiciones
- aprobaciÃ³n puntual

## PolÃ­ticas, secretos y artifacts

### PolÃ­ticas
- modelo hÃ­brido
- Supabase como configuraciÃ³n central
- runtime con cachÃ© local aplicada

### Secretos
- modelo hÃ­brido
- metadata/configuraciÃ³n en backend de producto
- secretos reales en entorno seguro del runtime
- nunca expuestos al frontend

### Artifacts
- modelo hÃ­brido
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
- configuraciÃ³n
- polÃ­ticas
- aprobaciÃ³n de acciones

#### Viewer / read-only
- ve dashboard
- ve agentes, eventos, mission room y artifacts visibles
- no cambia nada sensible

## Telegram vs Dashboard

### Telegram
Se usarÃ¡ para:
- notificaciones
- alertas
- decisiones rÃ¡pidas
- conflictos de prioridad
- aprobaciones pendientes
- bloqueos
- retries agotados
- misiÃ³n completada
- aviso de resumen disponible

### Dashboard
Se usarÃ¡ para:
- resÃºmenes completos
- historial
- anÃ¡lisis
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
- acceso a misiÃ³n activa

### Dentro de una misiÃ³n
- escena visual isomÃ©trica / 2.5D
- agentes como personajes con movimiento y actividad en tiempo real
- cards de agentes
- feed de eventos
- inspector del agente
- panel de misiÃ³n
- timeline
- artifacts

### Estilo visual
- hÃ­brido: tecnolÃ³gico + cÃ¡lido
- amigable
- premium
- con personalidad
- no corporativo frÃ­o

### Agent cards
Cada agente tendrÃ¡ card con:
- avatar acorde al personaje
- nombre
- rol
- personalidad breve
- estado actual
- tarea activa
- trabajo reciente
- artifacts recientes
- historial diario Ãºtil
- nivel de actividad
- bloqueo o salud operativa

## Visibilidad del trabajo interno

### PolÃ­tica
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

## CreaciÃ³n de misiones

Ambos:
- formulario simple
- wizard guiado

## Misiones programadas

- manuales + programadas
- soporte para seguimiento continuo, monitoreo, mantenimiento y campaÃ±as recurrentes

## Horario operativo

Mixto:
- ciertas tareas 24/7
- otras con ventanas horarias
- configurable segÃºn prioridad, misiÃ³n, integraciÃ³n o polÃ­tica

## Integraciones prioritarias v1
- Telegram
- Web search / fetch
- GitHub
- Google Maps / negocio local
- Instagram research / anÃ¡lisis

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
â”œâ”€â”€ README.md
â”œâ”€â”€ package.json
â”œâ”€â”€ .env.example
â”œâ”€â”€ .gitignore
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ MASTER_PLAN.md
â”‚   â”œâ”€â”€ SECURITY_MODEL.md
â”‚   â”œâ”€â”€ PRODUCT_REQUIREMENTS.md
â”‚   â”œâ”€â”€ AGENTS_OVERVIEW.md
â”‚   â””â”€â”€ TEMPLATES.md
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ agents.json
â”‚   â”œâ”€â”€ orchestrator.json
â”‚   â”œâ”€â”€ mission-templates.json
â”‚   â”œâ”€â”€ project.decisions.json
â”‚   â””â”€â”€ docker.future.json
â”œâ”€â”€ apps/
â”‚   â””â”€â”€ dashboard/
â”‚       â”œâ”€â”€ README.md
â”‚       â””â”€â”€ src/
â”‚           â””â”€â”€ placeholder.md
â”œâ”€â”€ prompts/
â”‚   â”œâ”€â”€ supervisor.AGENTS.md
â”‚   â”œâ”€â”€ researcher.AGENTS.md
â”‚   â”œâ”€â”€ designer.AGENTS.md
â”‚   â”œâ”€â”€ developer.AGENTS.md
â”‚   â””â”€â”€ qa.AGENTS.md
â”œâ”€â”€ runtime/
â”‚   â”œâ”€â”€ python/
â”‚   â”‚   â”œâ”€â”€ README.md
â”‚   â”‚   â”œâ”€â”€ requirements.txt
â”‚   â”‚   â”œâ”€â”€ main.py
â”‚   â”‚   â”œâ”€â”€ config.py
â”‚   â”‚   â”œâ”€â”€ db.py
â”‚   â”‚   â”œâ”€â”€ models.py
â”‚   â”‚   â”œâ”€â”€ planner.py
â”‚   â”‚   â”œâ”€â”€ policies.py
â”‚   â”‚   â”œâ”€â”€ notifications.py
â”‚   â”‚   â”œâ”€â”€ websocket_server.py
â”‚   â”‚   â””â”€â”€ templates.py
â”‚   â””â”€â”€ node-legacy/
â”‚       â””â”€â”€ README.md
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ legacy/
â”‚   â”‚   â”œâ”€â”€ agents.js
â”‚   â”‚   â”œâ”€â”€ context.js
â”‚   â”‚   â”œâ”€â”€ db.js
â”‚   â”‚   â”œâ”€â”€ logger.js
â”‚   â”‚   â”œâ”€â”€ main_orchestrator.js
â”‚   â”‚   â”œâ”€â”€ retry.js
â”‚   â”‚   â”œâ”€â”€ schema.sql
â”‚   â”‚   â”œâ”€â”€ supabase.js
â”‚   â”‚   â””â”€â”€ workflow.js
â”œâ”€â”€ supabase/
â”‚   â”œâ”€â”€ schema.sql
â”‚   â””â”€â”€ policies.sql
â”œâ”€â”€ data/
â”‚   â””â”€â”€ .gitkeep
â”œâ”€â”€ logs/
â”‚   â””â”€â”€ .gitkeep
â””â”€â”€ systemd/
    â””â”€â”€ virtual-agency.service
```

## AutomatizaciÃ³n operativa aÃ±adida

Virtual Agency ahora incluye un helper cron-friendly para sembrar automÃ¡ticamente una misiÃ³n `maintenance_cycle` cuando toque, sin duplicarla si ya hay una activa o si la Ãºltima ejecuciÃ³n sigue dentro de la ventana mÃ­nima.

Ejemplo:

```bash
npm run runtime:ensure-maintenance -- --min-interval-hours 24 --schedule-label cron:daily
```

El comando responde JSON (`created` o `skipped`) para que sea fÃ¡cil integrarlo con cron, systemd timers o scripts de health/ops.

## DiagnÃ³stico operativo

Para revisar rÃ¡pidamente si el runtime estÃ¡ sano, si el snapshot del dashboard estÃ¡ fresco, si hay trabajo bloqueado o si el WebSocket/systemd parecen caÃ­dos, ahora existe un comando de diagnÃ³stico orientado a operaciones:

```bash
npm run runtime:doctor
```

Opciones Ãºtiles:

```bash
npm run runtime:doctor -- --json
npm run runtime:doctor -- --snapshot-max-age-minutes 30
npm run runtime:doctor -- --systemd-unit virtual-agency.service
```

El diagnÃ³stico revisa:
- presencia y ubicaciÃ³n de la base SQLite
- misiÃ³n foco y estado general del runtime
- tareas/misiones bloqueadas
- necesidad potencial de recovery tras reinicio
- frescura de `apps/dashboard/public/snapshot.json` y `dist/snapshot.json`
- reachability del WebSocket configurado
- estado del unit de systemd si `systemctl` estÃ¡ disponible

## PrÃ³ximos pasos

1. Consolidar runtime Python + LangGraph
2. Definir dashboard Vite + React con login-first
3. Conectar Supabase Auth, roles y polÃ­ticas
4. Implementar planner, agenda avanzada y scheduling
5. Implementar event stream por WebSocket local
6. DiseÃ±ar cards, mission room y command center
7. AÃ±adir catÃ¡logo completo de plantillas
8. Preparar futura dockerizaciÃ³n por agente

---

# CI/CD y Testing

Virtual Agency incluye integraciÃ³n continua con GitHub Actions y una suite de pruebas automÃ¡ticas para el runtime Python.

## Ejecutar pruebas localmente

```bash
# Instalar dependencias de desarrollo
cd runtime/python
pip install -r requirements.txt
pip install -r requirements-test.txt

# Ejecutar todas las pruebas con cobertura
npm test
# o directamente:
cd runtime/python && python -m pytest -v --cov=. --cov-report=term-missing

# Generar reporte HTML de cobertura
cd runtime/python && python -m pytest --cov=. --cov-report=html
# Luego abrir htmlcov/index.html en el navegador
```

### Cobertura esperada
El objetivo de cobertura es >90% para el runtime Python (mÃ³dulos core: db, repository, config, models, scheduler, etc.)

## Flujo de CI/CD

El workflow de CI (.github/workflows/ci.yml) se ejecuta en:

- Push a `main`/`master`
- Pull requests hacia `main`/`master`
- Merge groups

### Pasos del workflow

1. **Setup Python**: Usa matrices para Python 3.11 y 3.12
2. **InstalaciÃ³n**: Instala dependencias de producciÃ³n y testing
3. **Tests**: Ejecuta pytest con coverage, genera reportes XML y terminal
4. **Upload a Codecov**: Sube la cobertura a codecov.io (opcional)
5. **Lint**: Ejecuta flake8 para detectar errores de estilo y calidad
6. **Build**: Solo en push a main, construye el dashboard (npm run build) y guarda artefacto

### Secrets requeridos en GitHub

ParaCodecov (opcional):
- `CODECOV_TOKEN`: Token de Codecov

## Notificaciones externas

Virtual Agency soporta notificaciones a travÃ©s de **Telegram** y **Slack**. Estas se usan para alertas, actualizaciones de misiÃ³n, bloqueos y decisiones que requieren intervenciÃ³n humana.

### Configurar Telegram

1. Crear un bot con [@BotFather](https://t.me/BotFather) y obtener el token
2. Obtener tu chat ID:
   - Enviar un mensaje a tu bot
   - Visitar `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Buscar el campo `"chat":{"id":123456789,...}`
3. Configurar variables de entorno:
   ```bash
   TELEGRAM_BOT_TOKEN=tu_bot_token
   TELEGRAM_CHAT_ID=tu_chat_id
   ```
4. Habilitar en el runtime: `MISSION_CONTROL_TELEGRAM_NOTIFICATIONS=true` (por defecto estÃ¡ true)

### Configurar Slack

1. Crear un Incoming Webhook en Slack:
   - Ve a tu workspace â†’ Apps â†’ "Incoming Webhooks"
   - ActÃ­talo y crea un nuevo webhook
   - Copia la URL (ej: `https://hooks.slack.com/services/T000/B000/XXXX`)
2. Configurar variable de entorno:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```
3. El webhook se activa automÃ¡ticamente si estÃ¡ configurado

### Tipos de notificaciones (kinds)

- `mission_complete`: MisiÃ³n completada
- `mission_failed`: MisiÃ³n fallÃ³
- `agent_blocked`: Agente bloqueado
- `error`: Error general del sistema
- `heartbeat`: Latido del sistema (silencioso, no notifica en Telegram)
- `progress`: ActualizaciÃ³n de progreso (opcionalmente silencioso)
- `alert`: Alertas generales

### Procesar notificaciones manualmente

El runtime procesa notificaciones automÃ¡ticamente cada tick. TambiÃ©n puedes procesar la cola manualmente:

```bash
# Procesar hasta 100 notificaciones pendientes
npm run runtime:notifications:process -- --limit 100

# Modo dry-run (simular sin enviar)
npm run runtime:notifications:process -- --dry-run

# Salida JSON
npm run runtime:notifications:process -- --json
```

### CLI deé€šçŸ¥ä¸‹ç§°å¤„ç†

El script `runtime/python/notification_processor_cli.py` permite procesar notificaciones desde la lÃ­nea de comandos, Ãºtil para cron jobs o debugging.

---

# Despliegue en ProducciÃ³n (VPS)

Virtual Agency incluye una configuraciÃ³n completa para despliegue 24/7 en un VPS usando Docker Compose.

## Requisitos del VPS

- **Sistema Operativo**: Ubuntu 22.04+ o Debian 11+ (x64 o ARM64)
- **Docker**: 20.10+ con Docker Compose v2
- **RAM**: MÃ­nimo 2GB, recomendado 4GB+
- **Almacenamiento**: 10GB libres (para base de datos, logs y contenedores)
- **Puertos**: 80 (HTTP) y opcionalmente 8765 (WebSocket)
- **Dominio** (opcional): Apuntando a la IP del VPS

## Estructura de despliegue

```text
MissionControl/
â”œâ”€â”€ deployment/
â”‚   â”œâ”€â”€ Dockerfile          # Imagen multi-stage (dashboard + runtime)
â”‚   â”œâ”€â”€ nginx.conf          # ConfiguraciÃ³n de nginx
â”‚   â”œâ”€â”€ start.sh            # Script de inicio del contenedor
â”‚   â””â”€â”€ init-db.sh          # Script de inicializaciÃ³n de BD
â”œâ”€â”€ docker-compose.yml      # OrquestaciÃ³n de contenedores
â”œâ”€â”€ .env.vps.example        # Variables de entorno de ejemplo
â”œâ”€â”€ .dockerignore           # Archivos excluidos del build
â””â”€â”€ ... (cÃ³digo fuente)
```

## Pasos de despliegue

### 1. Prepara el servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker y Compose
sudo apt install -y docker.io docker-compose

# AÃ±adir usuario actual a grupo docker (logout/login requerido)
sudo usermod -aG docker $USER
```

### 2. Clona el repositorio en el VPS

```bash
git clone <tu-repositorio> /opt/virtual-agency
cd /opt/virtual-agency
```

### 3. Configura variables de entorno

```bash
# Copiar el ejemplo
cp MissionControl/.env.vps.example .env.vps

# Editar con valores reales
nano .env.vps
```

Variables crÃ­ticas a configurar:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (si usas Supabase)
- `OPENROUTER_API_KEY` (para que los agentes puedan usar LLMs)
- `JWT_SECRET` (genera uno: `openssl rand -base64 32`)

> **Nota**: Si no configuras Supabase, Virtual Agency funcionarÃ¡ en modo standalone con SQLite local (solo para pruebas o uso personal).

### 4. Inicializar la base de datos

```bash
# Dar permisos de ejecuciÃ³n
chmod +x MissionControl/deployment/init-db.sh

# Inicializar (esto crea la SQLite y siembra los agentes iniciales)
MissionControl/deployment/init-db.sh .env.vps
```

### 5. Construir y levantar servicios

```bash
# Construir imagen Docker (solo primera vez o tras cambios)
docker-compose build

# Iniciar en modo detached (segundo plano)
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f
```

### 6. Verificar que todo funciona

```bash
# Salud del contenedor
docker-compose ps

# Health check (debe responder "healthy")
curl http://localhost/health

# Logs de la aplicaciÃ³n
docker-compose logs virtual-agency
```

### 7. Acceder al dashboard

Abre en tu navegador: `http://IP-DE-TU-VPS/`

- La primera carga puede tardar unos segundos mientras el runtimeåˆå§‹åŒ–.
- El dashboard se conecta automÃ¡ticamente via WebSocket a `ws://IP/ws`.
- Los agentes aparecerÃ¡n en estado `idle` hasta que se envÃ­e una misiÃ³n.

### 8. (Opcional) Configurar HTTPS con Let's Encrypt

Recomendamos usar **Caddy** o **nginx + certbot** para SSL gratis:

**Con Caddy (mÃ¡s simple)**:
```bash
# Instalar Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# Configurar Caddy para proxy a Virtual Agency (puerto 80)
sudo nano /etc/caddy/Caddyfile
```

Contenido de Caddyfile:
```
tu-dominio.com {
    reverse_proxy localhost:80
}
```

```bash
sudo systemctl reload caddy
```

## Comandos Ãºtiles de Docker Compose

```bash
# Reiniciar servicios
docker-compose restart

# Parar servicios
docker-compose down

# Parar y eliminar volÃºmenes (Â¡CUIDADO: borra la base de datos!)
docker-compose down -v

# Ver logs
docker-compose logs -f virtual-agency

# Acceder a shell del contenedor
docker-compose exec virtual-agency bash

# Rebuild tras cambios en el cÃ³digo
docker-compose build --no-cache
docker-compose up -d
```

## Directorios persistentes

- `./data` â†’ Base de datos SQLite y archivos temporales
- `./logs` â†’ Logs de la aplicaciÃ³n (dentro del contenedor)

Estos directorios estÃ¡n montados como volÃºmenes, por lo que sobreviven a recreaciones de contenedores.

## MonitorizaciÃ³n

### Healthcheck
Docker Compose verifica cada 30 segundos que `http://localhost/health` responde. El estado se ve con:
```bash
docker-compose ps
```

### Logs
Los logs del Python runtime y nginx se mezclan. Para filtar:
```bash
docker-compose logs -f virtual-agency | grep -i error
```

### RevisiÃ³n manual
```bash
# Estado de la base de datos
docker-compose exec virtual-agency python3 -c "from db import Database; db = Database('/app/data/sessions.db'); print('Missions:', db.fetchone('SELECT COUNT(*) as c FROM missions')['c'])"

# Generar snapshot inmediato
docker-compose exec virtual-agency python3 export_snapshot.py
```

## Copias de seguridad (Backup)

La base de datos es un archivo SQLite en `data/sessions.db`:

```bash
# Backup manual
cp data/sessions.db "backups/sessions-$(date +%Y%m%d-%H%M%S).db"

# Automatizar con cron (diario a las 2am)
0 2 * * * cp /opt/virtual-agency/data/sessions.db /opt/virtual-agency/backups/sessions-$(date +\%Y\%m\%d).db
```

## ActualizaciÃ³n

```bash
# 1. Pull de cambios
git pull origin main

# 2. Reconstruir imagen
docker-compose build

# 3. Reiniciar servicios
docker-compose up -d

# 4. Verificar logs
docker-compose logs -f
```

## SoluciÃ³n de problemas

### El contenedor se reinicia constantemente
Ver logs: `docker-compose logs virtual-agency`
- Error de conexiÃ³n a Supabase â†’ revisar `.env.vps`
- Puerto 80 ocupado â†’ cambiar puerto en `docker-compose.yml` o liberar puerto

### Base de datos corrupta
Eliminar volumen y reinicializar:
```bash
docker-compose down -v
rm -rf data/sessions.db
MissionControl/deployment/init-db.sh .env.vps
docker-compose up -d
```

### Dashboard no carga (blanco)
1. Verificar que nginx responde: `curl http://localhost/`
2. Verificar que el build existe: `ls -la apps/dashboard/dist/`
3. Si falta, reconstruir: `docker-compose build`
4. Verificar permisos: `ls -la data/`

### WebSocket no conecta
- Asegurarse de que `MISSION_CONTROL_WEBSOCKET=true` en `.env.vps`
- Verificar que el puerto 8765 no estÃ¡ bloqueado por firewall (si se accede externamente)
- En el dashboard, abrir consola del navegador (F12) y revisar errores de conexiÃ³n WebSocket

### Agentes no aparecen
- Esperar ~5 segundos (tick interval)
- Verificar que el runtime estÃ¡ vivo: `docker-compose logs virtual-agency | grep "Virtual Agency bootstrap"`
- Si no, puede que la base de datos no estÃ© inicializada

## MigraciÃ³n de base de datos

Si en el futuro se modifican las tablas, se agregarÃ¡n scripts de migraciÃ³n en `deployment/migrations/`. Por ahora, el esquema inicial es fijo y se aplica en `init-db.sh`.

Para migrar manualmente:
```bash
docker-compose exec virtual-agency python3 -c "
from db import Database
db = Database('/app/data/sessions.db')
# Ejecutar SQL manualmente
db.execute('ALTER TABLE missions ADD COLUMN nueva_columna TEXT')
"
```

## Seguridad en producciÃ³n

- Cambiar el usuario por defecto de nginx (se ejecuta como root por simplicidad; considerar usuario `nginx` en hardening)
- Configurar firewall (ufw/iptables) para solo abrir puertos 80/443
- Usar HTTPS (ver secciÃ³n anterior)
- Rotar secretos periÃ³dicamente
- No commitear `.env.vps` (ya estÃ¡ en `.gitignore`)
- Limitar logs (evitar log de secrets)
- Usar `restart: unless-stopped` en docker-compose (ya configurado)

## Soporte y contribuciones

Para reportar bugs o solicitar features, usar issues del repositorio.

---

*Desarrollado con â¤ï¸ para operaciones 24/7*



