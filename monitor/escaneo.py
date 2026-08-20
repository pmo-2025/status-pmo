#!/usr/bin/env python3
"""Escaneo rápido de todos los sitios de .upptimerc.yml.

Complementa a Upptime: Upptime tarda ~10 min por pasada y GitHub acaba
lanzándolo una vez cada 1-3 h, así que los microcortes (503 de unos minutos)
se pierden. Este escaneo hace las peticiones en paralelo (~60 s para 357
sitios), reintenta antes de dar nada por caído y avisa a Slack solo cuando
cambia el estado.
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTADO = os.path.join(RAIZ, "monitor", "estado.json")
INCIDENCIAS = os.path.join(RAIZ, "monitor", "incidencias.log")

CONCURRENCIA = 25
TIMEOUT = 20
INTENTOS = 3           # 3 fallos seguidos antes de dar un sitio por caído
ESPERA_REINTENTO = 25  # segundos entre intentos
# Una respuesta más corta que esto no es una web: es un parking, un
# defaultwebpage.cgi o un WordPress reventado. Medido el 29-jul sobre los 347
# sitios: los rotos daban 114-163 bytes y el sitio sano más pequeño 28.745,
# así que 5 KB deja margen de sobra por ambos lados.
MIN_BYTES = 5000
# Si cae más de este % de la lista (y al menos MIN_FALLO_MASIVO sitios), el
# problema es del runner/proxy, no de las webs: se avisa una sola vez en vez de
# escupir 300 falsas caídas, como pasó en julio con el proxy caducado.
UMBRAL_FALLO_MASIVO = 0.15
MIN_FALLO_MASIVO = 10

UA = "Mozilla/5.0 (compatible; MonitorPMO/1.0; +https://github.com/pmo-2025/status-pmo)"


# Redirecciones a otro dominio que son intencionadas y no hay que avisar,
# como pares (origen, destino) sin www.
BLANCA = {
    ("abriryrecuperar.com", "abriryrecuperar.es"),
}


def host(url):
    """Dominio de una URL, sin www, en punycode.

    Los dominios con ñ o tildes redirigen a su propia forma codificada
    (desatascos-coruña.com -> xn--desatascos-corua-lub.com): es la misma web,
    así que hay que comparar las dos en el mismo formato.
    """
    h = (urlparse(url).hostname or "").lower()
    if h.startswith("www."):
        h = h[4:]
    try:
        return h.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        return h


# PROXY_URLS admite varias URLs separadas por comas o saltos de línea. Se rota
# entre ellas para repartir la carga, y cada reintento sale por un proxy
# distinto: así una salida caída no tumba el escaneo entero, que es lo que pasó
# la madrugada del 20-ago (94-111 fallos a la vez con un solo proxy).
def lista_proxies():
    # PROXY_URLS (lista) para este escaneo; PROXY_URL (una sola) es la que
    # heredan Upptime y response-time como HTTP_PROXY, y ahí una lista
    # separada por comas no vale. Si no hay lista, se usa la de siempre.
    crudo = os.environ.get("PROXY_URLS", "") or os.environ.get("PROXY_URL", "")
    return [p for p in re.split(r"[,\s]+", crudo) if p]


PROXIES = lista_proxies()


def proxies(turno=0):
    if not PROXIES:
        return None
    url = PROXIES[turno % len(PROXIES)]
    return {"http": url, "https": url}


def sitios():
    with open(os.path.join(RAIZ, ".upptimerc.yml"), encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    return [(s["name"], s["url"]) for s in conf["sites"]]


def comprobar(url, sesion, turno=0):
    """Devuelve (ok, detalle)."""
    try:
        r = sesion.get(url, timeout=TIMEOUT, proxies=proxies(turno),
                       headers={"User-Agent": UA}, allow_redirects=True)
    except requests.exceptions.Timeout:
        return False, f"sin respuesta en {TIMEOUT}s"
    except requests.exceptions.RequestException as e:
        return False, f"error de conexión ({type(e).__name__})"

    tam = len(r.content)
    if r.status_code >= 400:
        return False, f"HTTP {r.status_code} · {tam} bytes"
    if tam < MIN_BYTES:
        return False, f"HTTP {r.status_code} · respuesta vacía ({tam} bytes)"

    # Acabar en otro dominio significa dominio caducado y recomprado, o
    # WordPress comprometido con redirección inyectada. Responde 200 y con
    # contenido de sobra, así que sin esto pasa por sano: hydrologicgroup.es
    # llevaba desde el 8-jul redirigiendo a una web de póker.
    origen, destino = host(url), host(r.url)
    if destino != origen and (origen, destino) not in BLANCA:
        return False, f"redirige a {destino} · revisar si está secuestrado"

    return True, f"HTTP {r.status_code} · {tam} bytes · {r.elapsed.total_seconds():.1f}s"


def barrer(lista, vuelta=0):
    """Comprueba una lista de (nombre, url) en paralelo.

    `vuelta` desplaza el reparto de proxies: en los reintentos cada sitio sale
    por una salida distinta de la que ya le falló.
    """
    resultados = {}
    with requests.Session() as sesion:
        def tarea(par):
            i, (nombre, url) = par
            return nombre, comprobar(url, sesion, i + vuelta)
        with ThreadPoolExecutor(max_workers=CONCURRENCIA) as pool:
            for nombre, res in pool.map(tarea, enumerate(lista)):
                resultados[nombre] = res
    return resultados


def cargar_estado():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def avisar_slack(texto):
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        print("SLACK_WEBHOOK_URL no configurado, no se envía aviso")
        return
    try:
        # Sin proxy: el webhook de Slack va directo, no a través del proxy de sitios
        r = requests.post(webhook, json={"text": texto}, timeout=15)
        print(f"Aviso a Slack: HTTP {r.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"No se pudo avisar a Slack: {e}")


def main():
    # La salida lleva acentos: sin esto revienta en consolas cp1252 (Windows)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    lista = sitios()
    ahora = datetime.now(timezone.utc)
    sello = ahora.isoformat(timespec="seconds")
    print(f"[{sello}] escaneando {len(lista)} sitios...")

    resultados = barrer(lista)
    fallos = {n: d for n, (ok, d) in resultados.items() if not ok}
    print(f"primera pasada: {len(fallos)} fallos")

    # Reintentos solo sobre los que fallaron
    for intento in range(2, INTENTOS + 1):
        if not fallos:
            break
        time.sleep(ESPERA_REINTENTO)
        repetir = [(n, u) for n, u in lista if n in fallos]
        segunda = barrer(repetir, vuelta=intento)
        fallos = {n: d for n, (ok, d) in segunda.items() if not ok}
        print(f"intento {intento}: {len(fallos)} fallos")
        for n, (ok, d) in segunda.items():
            resultados[n] = (ok, d)

    caidos = sorted(fallos)

    if len(caidos) >= MIN_FALLO_MASIVO and len(caidos) > len(lista) * UMBRAL_FALLO_MASIVO:
        aviso = (f":warning: *Escaneo no fiable*: {len(caidos)} de {len(lista)} sitios "
                 f"dan error a la vez. Casi seguro es el proxy o la red del runner, "
                 f"no las webs. No se ha actualizado el estado.")
        print(aviso)
        avisar_slack(aviso)
        return 0

    anterior = cargar_estado()
    nuevo = {}
    nuevas_caidas, recuperados = [], []

    for nombre, (ok, detalle) in resultados.items():
        previo = anterior.get(nombre, {})
        estaba_caido = previo.get("estado") == "caido"
        if ok:
            nuevo[nombre] = {"estado": "ok", "detalle": detalle}
            if estaba_caido:
                desde = previo.get("desde", "?")
                recuperados.append((nombre, desde, detalle))
        else:
            desde = previo.get("desde", sello) if estaba_caido else sello
            nuevo[nombre] = {"estado": "caido", "desde": desde, "detalle": detalle}
            if not estaba_caido:
                nuevas_caidas.append((nombre, detalle))

    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(nuevo, f, indent=1, ensure_ascii=False, sort_keys=True)

    lineas = []
    for nombre, detalle in nuevas_caidas:
        lineas.append(f"{sello}\tCAIDA\t{nombre}\t{detalle}")
    for nombre, desde, detalle in recuperados:
        lineas.append(f"{sello}\tRECUPERADO\t{nombre}\tcaído desde {desde}")
    if lineas:
        with open(INCIDENCIAS, "a", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")

    if nuevas_caidas:
        cuerpo = "\n".join(f"• *{n}* — {d}" for n, d in sorted(nuevas_caidas))
        avisar_slack(f":red_circle: *{len(nuevas_caidas)} web(s) caídas*\n{cuerpo}")
    if recuperados:
        cuerpo = "\n".join(f"• *{n}* (caída desde {desde})" for n, desde, _ in sorted(recuperados))
        avisar_slack(f":large_green_circle: *{len(recuperados)} web(s) recuperadas*\n{cuerpo}")

    print(f"caídos ahora: {len(caidos)} | nuevas caídas: {len(nuevas_caidas)} | "
          f"recuperados: {len(recuperados)}")
    for nombre in caidos:
        print(f"  ✗ {nombre} — {fallos[nombre]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
