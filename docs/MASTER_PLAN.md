# Mission Control - Master Plan

Este documento consolida la visión, arquitectura, producto, seguridad y operación definidos para Mission Control.

## Resumen ejecutivo
Mission Control será un centro de operaciones multiagente autónomo, visual, seguro y persistente, capaz de trabajar en desarrollo, marketing, auditoría digital y ejecución híbrida, con 5 agentes base, agenda avanzada, políticas granulares y dashboard vivo.

## Núcleo fijo
- Supervisor
- Researcher
- Designer
- Developer
- QA

## Modos y plantillas
El sistema funcionará con plantillas amplias y modos de misión para evitar agregar demasiados agentes y mantener el runtime eficiente.

## Arquitectura
- Frontend: Vercel + Vite + React
- Backend de producto: Supabase
- Runtime: Python + LangGraph + SQLite + WebSocket local

## Seguridad
- login-first
- magic link
- secretos fuera del código
- RLS
- guardrails
- permisos granulares
- acciones externas solo por políticas explícitas

## Tiempo real
- dashboard con cards de agentes
- command center
- mission room
- inspector del agente
- feed de eventos

## Autonomía
Alta, con escalamiento solo cuando hay ambigüedad, riesgo, conflicto, credenciales faltantes o retries agotados.
