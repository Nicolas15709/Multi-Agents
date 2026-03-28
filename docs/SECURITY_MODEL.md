# Security Model

## Objetivo
Diseñar Mission Control con seguridad por defecto, separación de privilegios y sin exposición de secretos.

## Principios
- Nada de secretos hardcodeados
- Nada de tokens en frontend
- Variables de entorno para secretos operativos
- Supabase anon key solo para cliente cuando corresponda
- Service role nunca en frontend
- Runtime como frontera privilegiada
- RLS obligatorio
- mínimo privilegio por rol y por agente
- validación de inputs en frontend y runtime
- queries parametrizadas
- logs sin datos sensibles
- políticas granulares por integración/cuenta/acción
- sin política explícita, no se ejecuta

## Amenazas consideradas
- exposición de secretos
- SQL injection
- XSS
- CSRF donde aplique
- SSRF en integraciones futuras
- abuso de actions externas
- escalamiento indebido de permisos
- filtrado excesivo de razonamiento interno

## Decisiones operativas
- Telegram como canal de notificación, no como volcado de resúmenes largos
- Dashboard para resúmenes y trazabilidad
- Viewer sin acceso a secretos ni configuración sensible
- runtime con caché local de políticas

## Futuro Docker
Cada agente tendrá aislamiento, networking controlado, secretos mínimos y filesystem acotado.
