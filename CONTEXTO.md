# Proyecto: Monitor de uptime para webs PMO con Upptime

## Objetivo
Monitorizar diariamente ~200 webs de clientes de la agencia PMO para detectar caídas. Recibir alertas por email y Slack. Solución gratuita, sin VPS propio.

## Stack elegido
**Upptime** (https://github.com/upptime/upptime): monitor de uptime open-source que funciona con GitHub Actions. El repo en GitHub hace pings programados a las URLs, abre issues automáticamente cuando hay caída, manda alertas y genera un status page público.

Razones de elección sobre otras opciones:
- No requiere VPS propio (descartado Uptime Kuma en VPS Hetzner existente para no chocar con otras webs/apps ya corriendo, y para no tener que vigilar al vigilante).
- Gratis e ilimitado en repos públicos.
- 17k+ estrellas, mantenido activamente (último cambio mayo 2026), usado por Canonical entre otros.

## Estado actual (pasos completados)

### Paso 1 ✅ Repositorio creado
- Repo: `pmo-2025/status-pmo` (público)
- Creado desde plantilla oficial `upptime/upptime` con "Use this template"
- Archivo `.upptimerc.yml` presente en la raíz

### Paso 2 ✅ Personal Access Token generado
- Tipo: Fine-grained personal access token
- Nombre: `upptime-token`
- Expiración: never expire
- Repo access: solo `pmo-2025/status-pmo`
- Permisos: Actions (R/W), Administration (R/W), Contents (R/W), Issues (R/W), Metadata (Read-only auto)

### Paso 3 ✅ Token guardado como secret
- Ubicación: Settings → Secrets and variables → Actions
- Nombre del secret: `GH_PAT`
- Valor: el token generado en paso 2

### Paso 4 ✅ Repo clonado y Claude Code abierto
- Repo clonado localmente
- Claude Code activo dentro de la carpeta `status-pmo`
- Excel con las ~200 URLs ya leído por Claude Code en la sesión anterior

## Pasos pendientes

### Paso 5: Generar .upptimerc.yml con las 200 URLs
Procedimiento previsto:
1. Leer Excel: detectar columnas (URLs y nombres si los hay), mostrar muestra al usuario.
2. Comprobar con curl si cada dominio responde por https (códigos 200/301/302). Si no responde por https, probar http. Si no responde por ninguno, marcar como "revisar". Hacerlo en paralelo. Mostrar resumen: cuántas en https, cuántas en http, cuántas a revisar.
3. **Esperar confirmación del usuario antes de seguir.**
4. Cuando el usuario diga adelante, generar `.upptimerc.yml` modificando SOLO:
   - `owner: pmo-2025`
   - `repo: status-pmo`
   - sección `sites:` con todas las URLs (cada una con `name` y `url`)
   - Si no había nombres en el Excel, usar el dominio como name.
   - **NO tocar** notifications, status-website ni otras secciones todavía.
5. **NO hacer git add/commit/push.** Guardar localmente para que el usuario revise antes de subir.

### Paso 6 (pendiente): Configurar notificaciones
Canales deseados: **Email + Slack** (multicanal).
Documentación de referencia: https://upptime.js.org/docs/notifications

### Paso 7 (pendiente): Ajustar frecuencia de checks
Frecuencia deseada: **1 vez al día** (resumen diario).
La frecuencia se configura en los archivos de workflow dentro de `.github/workflows/`.

### Paso 8 (pendiente): Primer push y verificar que GitHub Actions ejecuta correctamente

## Preferencias del usuario (Fernando) — IMPORTANTES
- Ir paso a paso: hacer paso 1, comprobar, pasar al paso 2. **NUNCA varios pasos a la vez.**
- Siempre investigar antes de proponer cambios.
- En código: **no romper otras partes ni hacer cambios sin permiso explícito.**
- Comunicación en español, tono casual.
- Si hay dudas, **preguntar antes de asumir.**

## Datos clave
- GitHub user / org: `pmo-2025`
- Repo: `pmo-2025/status-pmo`
- Secret name en el repo: `GH_PAT`
- Excel con URLs: dentro de la carpeta del repo (Claude Code ya lo tenía leído)
- Las URLs son dominios sueltos sin `https://` delante (ej: `electricistasleon.com`)
- Mezcla de http/https desconocida: hay que comprobar caso por caso

## Contexto adicional Fernando
- Agencia PMO (agenciapmonline@gmail.com), Valencia, España
- Stack habitual: WordPress, Claude Code + VS Code, Supabase
- Clientes: cerrajeros, fontaneros, electricistas, tapicerías, etc. en ciudades españolas
- VPS Hetzner Cloud existente con producción (NO usar para este proyecto)

## Cómo retomar
El usuario abrirá Claude Code en esta misma carpeta y dirá algo como:
> "Lee CONTEXTO.md y dime por dónde íbamos. Continúa desde ahí siguiendo mis preferencias."

A partir de ahí, continuar por el **Paso 5** respetando las preferencias del usuario (un paso, esperar confirmación, siguiente paso).
