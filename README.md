# Monitorización de webs — PMO

Vigila que las **342 webs** de la agencia estén online y avisa por Slack cuando
una se cae.

## Cómo funciona

Cada ~9 minutos se comprueban todas las webs en paralelo (tarda unos 25 segundos)
y de cada una se mira:

1. **Que responda.** Sin respuesta o error 4xx/5xx, es una caída.
2. **Que sirva la web de verdad.** Menos de 5 KB no es una web: es el parking del
   registrador, la página por defecto de cPanel o un WordPress reventado. Esto no
   lo pilla un monitor normal, porque el servidor contesta `200 OK`.
3. **Que no acabe en otro dominio.** Si la web redirige fuera, el dominio puede
   estar caducado y recomprado, o el WordPress comprometido con una redirección
   inyectada.

Antes de dar nada por caído se prueba **3 veces separadas 25 segundos**, para no
avisar por un pico del hosting. Y si falla más del 15 % de la lista a la vez, se
asume que el problema es el proxy o la red, no las webs, y no se marca nada: es lo
que provocó los 124 avisos falsos de julio de 2026.

## Dónde mirar

| Fichero | Qué contiene |
|---|---|
| [`monitor/incidencias.log`](monitor/incidencias.log) | Histórico de cortes con hora de caída y de recuperación |
| [`monitor/estado.json`](monitor/estado.json) | Estado actual de cada web |
| [`monitor/escaneo.py`](monitor/escaneo.py) | El escaneo |

Los avisos llegan a Slack por webhook (secret `SLACK_WEBHOOK_URL`), solo cuando
algo **cambia** de estado. Nada de repetir el mismo aviso cada nueve minutos.

## Añadir o quitar una web

Se edita la lista `sites` de [`.upptimerc.yml`](.upptimerc.yml). Al quitar una,
hay que borrar también sus datos y cerrar su issue si lo tiene:

```bash
rm -f history/<slug>.yml
rm -rf api/<slug> graphs/<slug>
gh issue close <numero> --repo pmo-2025/status-pmo
```

El *slug* es el dominio con guiones en vez de puntos: `cerrajerosleon.com` →
`cerrajerosleon-com`. Los dominios con ñ o tilde van sin acentos
(`desatascos-coruña.com` → `desatascos-coruna-com`).

## Sobre Upptime

El repo nació como [Upptime](https://upptime.js.org) y sigue guardando el
histórico en `history/`, pero la detección ya no depende de él: GitHub throttlea
los workflows programados y acababa ejecutándolo **una vez cada 1-3 horas**, así
que se le escapaba cualquier caída de menos de una hora.

Workflows desactivados a propósito:

- **Static Site CI**, **Graphs CI** y **Summary CI**: solo generaban la página de
  estado pública y sus 1.785 gráficos. La página se retiró en julio de 2026.
- **Updates CI** y **Update Template CI**: reescribían los workflows con la
  plantilla oficial de Upptime y se cargaban la configuración del proxy, que es
  justo lo que provocó los falsos positivos de julio.

Sigue activo **Response Time CI**, que manda dos resúmenes diarios por email y
Slack con las webs lentas y los certificados SSL a punto de caducar.
