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

### Sistema de Memoria (Vector + Sesión)
- **Memoria Vectorial**: Supabase pgvector para búsqueda semántica a largo plazo (experiencias, eventos, artifacts)
- **Memoria por Sesión**: SQLite local con state diffing y snapshots comprimidos (estado en tiempo real)
- **Embeddings**: OpenAI o Groq (text-embedding-ada-002)
- **TTL automático**: Políticas configurables de retención y limpieza
- **Sync**: Cola de sincronización para consistencia eventual

> Consulta `MEMORY.md` para la guía completa de configuración, API y operación.

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

## Automatización operativa añadida

Mission Control ahora incluye un helper cron-friendly para sembrar automáticamente una misión `maintenance_cycle` cuando toque, sin duplicarla si ya hay una activa o si la última ejecución sigue dentro de la ventana mínima.

Ejemplo:

```bash
npm run runtime:ensure-maintenance -- --min-interval-hours 24 --schedule-label cron:daily
```

El comando responde JSON (`created` o `skipped`) para que sea fácil integrarlo con cron, systemd timers o scripts de health/ops.

## Diagnóstico operativo

Para revisar rápidamente si el runtime está sano, si el snapshot del dashboard está fresco, si hay trabajo bloqueado o si el WebSocket/systemd parecen caídos, ahora existe un comando de diagnóstico orientado a operaciones:

```bash
npm run runtime:doctor
```

Opciones útiles:

```bash
npm run runtime:doctor -- --json
npm run runtime:doctor -- --snapshot-max-age-minutes 30
npm run runtime:doctor -- --systemd-unit mission-control.service
```

El diagnóstico revisa:
- presencia y ubicación de la base SQLite
- misión foco y estado general del runtime
- tareas/misiones bloqueadas
- necesidad potencial de recovery tras reinicio
- frescura de `apps/dashboard/public/snapshot.json` y `dist/snapshot.json`
- reachability del WebSocket configurado
- estado del unit de systemd si `systemctl` está disponible

## Próximos pasos

1. Consolidar runtime Python + LangGraph
2. Definir dashboard Vite + React con login-first
3. Conectar Supabase Auth, roles y políticas
4. Implementar planner, agenda avanzada y scheduling
5. Implementar event stream por WebSocket local
6. Diseñar cards, mission room y command center
7. Añadir catálogo completo de plantillas
8. Preparar futura dockerización por agente

---

# CI/CD y Testing

Mission Control incluye integración continua con GitHub Actions y una suite de pruebas automáticas para el runtime Python.

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
El objetivo de cobertura es >90% para el runtime Python (módulos core: db, repository, config, models, scheduler, etc.)

## Flujo de CI/CD

El workflow de CI (.github/workflows/ci.yml) se ejecuta en:

- Push a `main`/`master`
- Pull requests hacia `main`/`master`
- Merge groups

### Pasos del workflow

1. **Setup Python**: Usa matrices para Python 3.11 y 3.12
2. **Instalación**: Instala dependencias de producción y testing
3. **Tests**: Ejecuta pytest con coverage, genera reportes XML y terminal
4. **Upload a Codecov**: Sube la cobertura a codecov.io (opcional)
5. **Lint**: Ejecuta flake8 para detectar errores de estilo y calidad
6. **Build**: Solo en push a main, construye el dashboard (npm run build) y guarda artefacto

### Secrets requeridos en GitHub

ParaCodecov (opcional):
- `CODECOV_TOKEN`: Token de Codecov

## Notificaciones externas

Mission Control soporta notificaciones a través de **Telegram** y **Slack**. Estas se usan para alertas, actualizaciones de misión, bloqueos y decisiones que requieren intervención humana.

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
4. Habilitar en el runtime: `MISSION_CONTROL_TELEGRAM_NOTIFICATIONS=true` (por defecto está true)

### Configurar Slack

1. Crear un Incoming Webhook en Slack:
   - Ve a tu workspace → Apps → "Incoming Webhooks"
   - Actítalo y crea un nuevo webhook
   - Copia la URL (ej: `https://hooks.slack.com/services/T000/B000/XXXX`)
2. Configurar variable de entorno:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```
3. El webhook se activa automáticamente si está configurado

### Tipos de notificaciones (kinds)

- `mission_complete`: Misión completada
- `mission_failed`: Misión falló
- `agent_blocked`: Agente bloqueado
- `error`: Error general del sistema
- `heartbeat`: Latido del sistema (silencioso, no notifica en Telegram)
- `progress`: Actualización de progreso (opcionalmente silencioso)
- `alert`: Alertas generales

### Procesar notificaciones manualmente

El runtime procesa notificaciones automáticamente cada tick. También puedes procesar la cola manualmente:

```bash
# Procesar hasta 100 notificaciones pendientes
npm run runtime:notifications:process -- --limit 100

# Modo dry-run (simular sin enviar)
npm run runtime:notifications:process -- --dry-run

# Salida JSON
npm run runtime:notifications:process -- --json
```

### CLI de通知下称处理

El script `runtime/python/notification_processor_cli.py` permite procesar notificaciones desde la línea de comandos, útil para cron jobs o debugging.

---

# Despliegue en Producción (VPS)

Mission Control incluye una configuración completa para despliegue 24/7 en un VPS usando Docker Compose.

## Requisitos del VPS

- **Sistema Operativo**: Ubuntu 22.04+ o Debian 11+ (x64 o ARM64)
- **Docker**: 20.10+ con Docker Compose v2
- **RAM**: Mínimo 2GB, recomendado 4GB+
- **Almacenamiento**: 10GB libres (para base de datos, logs y contenedores)
- **Puertos**: 80 (HTTP) y opcionalmente 8765 (WebSocket)
- **Dominio** (opcional): Apuntando a la IP del VPS

## Estructura de despliegue

```text
MissionControl/
├── deployment/
│   ├── Dockerfile          # Imagen multi-stage (dashboard + runtime)
│   ├── nginx.conf          # Configuración de nginx
│   ├── start.sh            # Script de inicio del contenedor
│   └── init-db.sh          # Script de inicialización de BD
├── docker-compose.yml      # Orquestación de contenedores
├── .env.vps.example        # Variables de entorno de ejemplo
├── .dockerignore           # Archivos excluidos del build
└── ... (código fuente)
```

## Pasos de despliegue

### 1. Prepara el servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker y Compose
sudo apt install -y docker.io docker-compose

# Añadir usuario actual a grupo docker (logout/login requerido)
sudo usermod -aG docker $USER
```

### 2. Clona el repositorio en el VPS

```bash
git clone <tu-repositorio> /opt/mission-control
cd /opt/mission-control
```

### 3. Configura variables de entorno

```bash
# Copiar el ejemplo
cp MissionControl/.env.vps.example .env.vps

# Editar con valores reales
nano .env.vps
```

Variables críticas a configurar:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (si usas Supabase)
- `OPENROUTER_API_KEY` (para que los agentes puedan usar LLMs)
- `JWT_SECRET` (genera uno: `openssl rand -base64 32`)

> **Nota**: Si no configuras Supabase, Mission Control funcionará en modo standalone con SQLite local (solo para pruebas o uso personal).

### 4. Inicializar la base de datos

```bash
# Dar permisos de ejecución
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

# Logs de la aplicación
docker-compose logs mission-control
```

### 7. Acceder al dashboard

Abre en tu navegador: `http://IP-DE-TU-VPS/`

- La primera carga puede tardar unos segundos mientras el runtime初始化.
- El dashboard se conecta automáticamente via WebSocket a `ws://IP/ws`.
- Los agentes aparecerán en estado `idle` hasta que se envíe una misión.

### 8. (Opcional) Configurar HTTPS con Let's Encrypt

Recomendamos usar **Caddy** o **nginx + certbot** para SSL gratis:

**Con Caddy (más simple)**:
```bash
# Instalar Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# Configurar Caddy para proxy a Mission Control (puerto 80)
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

## Comandos útiles de Docker Compose

```bash
# Reiniciar servicios
docker-compose restart

# Parar servicios
docker-compose down

# Parar y eliminar volúmenes (¡CUIDADO: borra la base de datos!)
docker-compose down -v

# Ver logs
docker-compose logs -f mission-control

# Acceder a shell del contenedor
docker-compose exec mission-control bash

# Rebuild tras cambios en el código
docker-compose build --no-cache
docker-compose up -d
```

## Directorios persistentes

- `./data` → Base de datos SQLite y archivos temporales
- `./logs` → Logs de la aplicación (dentro del contenedor)

Estos directorios están montados como volúmenes, por lo que sobreviven a recreaciones de contenedores.

## Monitorización

### Healthcheck
Docker Compose verifica cada 30 segundos que `http://localhost/health` responde. El estado se ve con:
```bash
docker-compose ps
```

### Logs
Los logs del Python runtime y nginx se mezclan. Para filtar:
```bash
docker-compose logs -f mission-control | grep -i error
```

### Revisión manual
```bash
# Estado de la base de datos
docker-compose exec mission-control python3 -c "from db import Database; db = Database('/app/data/sessions.db'); print('Missions:', db.fetchone('SELECT COUNT(*) as c FROM missions')['c'])"

# Generar snapshot inmediato
docker-compose exec mission-control python3 export_snapshot.py
```

## Copias de seguridad (Backup)

La base de datos es un archivo SQLite en `data/sessions.db`:

```bash
# Backup manual
cp data/sessions.db "backups/sessions-$(date +%Y%m%d-%H%M%S).db"

# Automatizar con cron (diario a las 2am)
0 2 * * * cp /opt/mission-control/data/sessions.db /opt/mission-control/backups/sessions-$(date +\%Y\%m\%d).db
```

## Actualización

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

## Solución de problemas

### El contenedor se reinicia constantemente
Ver logs: `docker-compose logs mission-control`
- Error de conexión a Supabase → revisar `.env.vps`
- Puerto 80 ocupado → cambiar puerto en `docker-compose.yml` o liberar puerto

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
- Verificar que el puerto 8765 no está bloqueado por firewall (si se accede externamente)
- En el dashboard, abrir consola del navegador (F12) y revisar errores de conexión WebSocket

### Agentes no aparecen
- Esperar ~5 segundos (tick interval)
- Verificar que el runtime está vivo: `docker-compose logs mission-control | grep "Mission Control bootstrap"`
- Si no, puede que la base de datos no esté inicializada

## Migración de base de datos

Si en el futuro se modifican las tablas, se agregarán scripts de migración en `deployment/migrations/`. Por ahora, el esquema inicial es fijo y se aplica en `init-db.sh`.

Para migrar manualmente:
```bash
docker-compose exec mission-control python3 -c "
from db import Database
db = Database('/app/data/sessions.db')
# Ejecutar SQL manualmente
db.execute('ALTER TABLE missions ADD COLUMN nueva_columna TEXT')
"
```

## Seguridad en producción

- Cambiar el usuario por defecto de nginx (se ejecuta como root por simplicidad; considerar usuario `nginx` en hardening)
- Configurar firewall (ufw/iptables) para solo abrir puertos 80/443
- Usar HTTPS (ver sección anterior)
- Rotar secretos periódicamente
- No commitear `.env.vps` (ya está en `.gitignore`)
- Limitar logs (evitar log de secrets)
- Usar `restart: unless-stopped` en docker-compose (ya configurado)

## Soporte y contribuciones

Para reportar bugs o solicitar features, usar issues del repositorio.

---

*Desarrollado con ❤️ para operaciones 24/7*

