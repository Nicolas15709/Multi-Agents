# Virtual Agency - Master Plan

Este documento consolida la visiÃ³n, arquitectura, producto, seguridad y operaciÃ³n definidos para Virtual Agency.

## Resumen ejecutivo
Virtual Agency serÃ¡ un centro de operaciones multiagente autÃ³nomo, visual, seguro y persistente, capaz de trabajar en desarrollo, marketing, auditorÃ­a digital y ejecuciÃ³n hÃ­brida, con 5 agentes base, agenda avanzada, polÃ­ticas granulares y dashboard vivo.

## NÃºcleo fijo
- Supervisor
- Researcher
- Designer
- Developer
- QA

## Modos y plantillas
El sistema funcionarÃ¡ con plantillas amplias y modos de misiÃ³n para evitar agregar demasiados agentes y mantener el runtime eficiente.

## Arquitectura
- Frontend: Vercel + Vite + React
- Backend de producto: Supabase
- Runtime: Python + LangGraph + SQLite + WebSocket local

## Seguridad
- login-first
- magic link
- secretos fuera del cÃ³digo
- RLS
- guardrails
- permisos granulares
- acciones externas solo por polÃ­ticas explÃ­citas

## Tiempo real
- dashboard con cards de agentes
- command center
- mission room
- inspector del agente
- feed de eventos

## AutonomÃ­a
Alta, con escalamiento solo cuando hay ambigÃ¼edad, riesgo, conflicto, credenciales faltantes o retries agotados.

