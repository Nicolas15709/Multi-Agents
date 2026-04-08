# 🧠 Obsidian Memory Integration

Tu bóveda de Obsidian (`C:\Users\Nicolas\Documents\Memoria Boveda`) es ahora el **hub de memoria** para tus agentes multi-agents.

---

## 🚀 Cómo Usar

### 1. Guardar Misiones Automáticamente

En `runtime/python/main.py`, después de que una misión se completa:

```python
from obsidian_memory import ObsidianMemory, hook_mission_completed

# Dentro de tu código de completación de misiones:
obsidian = ObsidianMemory()
hook_mission_completed(mission, tasks, obsidian)

# O manualmente:
obsidian.save_mission(mission, tasks)
```

### 2. Guardar Learnings

Cuando descubres un insight importante:

```python
obsidian.save_learning(
    title="Optimización de API response time",
    insight="Usar caching en endpoints de lectura reduce latency 60%",
    theme="technical",
    agents=["Developer", "QA"],
    mission_id="mission-20260405-001"
)
```

### 3. Guardar Decisiones

Cuando tomas una decisión arquitectónica:

```python
obsidian.save_decision(
    title="Usar Tailwind CSS en dashboard",
    decision="Adoptamos Tailwind como framework CSS principal",
    reasoning="Desarrollo más rápido, built-in design tokens, comunidad grande",
    impact="arquitectura"
)
```

### 4. Inyectar Contexto en Prompts de Agentes

Antes de enviar un prompt a un agente, incluye el contexto de Obsidian:

```python
context = obsidian.get_agent_context(agent_name="Developer")

system_prompt = f"""
You are a Developer agent.

## Contexto Reciente
{context}

## Tu Tarea
[task description]
"""
```

---

## 📁 Estructura Creada

```
Memoria Boveda/
├── missions/               # Misiones completadas (una por día)
├── learnings/
│   ├── technical/          # Insights técnicos
│   ├── market/             # Hallazgos de market research
│   └── process/            # Patrones de procesos
├── decisions/              # Decisiones importantes
├── patterns/               # Patrones emergentes (agregar manual)
├── templates/
│   ├── mission.md
│   ├── learning.md
│   ├── decision.md
│   └── pattern.md
└── [resto de carpetas]
```

---

## 🔄 Flujo Recomendado

```
1. Mission ejecuta
   ↓
2. Python guarda automáticamente en missions/
   ↓
3. TÚ revisas los resultados en Obsidian
   ↓
4. TÚ extraes learnings y los creas en learnings/
   ↓
5. Próxima misión: Agentes leen contexto reciente con get_agent_context()
   ↓
6. Ciclo continúa con memoria acumulada
```

---

## 🎯 Ejemplo Completo

```python
# En main.py, dentro de tu mission completion handler:

from obsidian_memory import ObsidianMemory

obsidian = ObsidianMemory()

# Cuando mission termina
if mission.status == "completed":
    obsidian.save_mission(mission, tasks)

    # Inyectar contexto en próxima iteración
    context = obsidian.get_agent_context()
    # ... usar en prompts
```

---

## 📝 Qué Guardar Dónde

| Tipo | Carpeta | Cuándo | Quién |
|------|---------|--------|-------|
| **Mission** | `missions/` | Se completa una misión | Python (automático) |
| **Learning** | `learnings/` | Descubres un insight importante | Tú (manual) |
| **Decision** | `decisions/` | Tomas una decisión clave | Tú (manual) |
| **Pattern** | `patterns/` | Notas un patrón recurrente | Tú (manual) |

---

## ⚙️ Configuración

Si tu vault está en otra ruta:

```python
obsidian = ObsidianMemory(vault_path="C:\\Users\\Nicolas\\Documents\\OtroLugar")
```

---

## 🔗 Links Útiles

- [CLAUDE.md](./CLAUDE.md) — Convenciones de la bóveda
- [Obsidian Docs](https://obsidian.md/)
- [Templates](./templates/) — Plantillas para cada tipo de nota
