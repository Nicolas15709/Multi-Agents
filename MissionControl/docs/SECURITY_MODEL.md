# Security Model

## Objetivo
DiseÃ±ar Virtual Agency con seguridad por defecto, separaciÃ³n de privilegios y sin exposiciÃ³n de secretos.

## Principios
- Nada de secretos hardcodeados
- Nada de tokens en frontend
- Variables de entorno para secretos operativos
- Supabase anon key solo para cliente cuando corresponda
- Service role nunca en frontend
- Runtime como frontera privilegiada
- RLS obligatorio
- mÃ­nimo privilegio por rol y por agente
- validaciÃ³n de inputs en frontend y runtime
- queries parametrizadas
- logs sin datos sensibles
- polÃ­ticas granulares por integraciÃ³n/cuenta/acciÃ³n
- sin polÃ­tica explÃ­cita, no se ejecuta

## Amenazas consideradas
- exposiciÃ³n de secretos
- SQL injection
- XSS
- CSRF donde aplique
- SSRF en integraciones futuras
- abuso de actions externas
- escalamiento indebido de permisos
- filtrado excesivo de razonamiento interno

## Decisiones operativas
- Telegram como canal de notificaciÃ³n, no como volcado de resÃºmenes largos
- Dashboard para resÃºmenes y trazabilidad
- Viewer sin acceso a secretos ni configuraciÃ³n sensible
- runtime con cachÃ© local de polÃ­ticas

## Futuro Docker
Cada agente tendrÃ¡ aislamiento, networking controlado, secretos mÃ­nimos y filesystem acotado.

