"""
Prueba de carga — Café Express Distribuido

Lanza N pedidos concurrentes contra el Gateway y mide:
  - Tiempo de respuesta de creación del pedido (POST /pedidos), que debe
    mantenerse bajo y estable sin importar N, porque Orders responde
    apenas guarda el pedido y delega el resto de forma asíncrona.
  - Tiempo total hasta que TODOS los pedidos llegan a estado ENTREGADO
    (procesamiento de extremo a extremo), que sí depende de N y del
    tamaño de los pools de hilos de Kitchen/Dispatch.
  - Throughput (pedidos entregados / segundo).

Uso:
    python load_test.py --niveles 10 25 50 100
    python load_test.py --niveles 10 25 50 100 --salida resultados.json
"""
import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

GATEWAY_URL = "http://localhost:8000"
POLL_INTERVAL = 0.2
POLL_TIMEOUT = 90


def crear_pedido(i: int) -> dict:
    t0 = time.perf_counter()
    resp = requests.post(
        f"{GATEWAY_URL}/pedidos",
        json={
            "cliente": f"cliente-carga-{i}",
            "items": [{"producto": "Café", "cantidad": 1, "precio_unitario": 3500}],
        },
        timeout=15,
    )
    latencia = time.perf_counter() - t0
    resp.raise_for_status()
    pedido = resp.json()
    return {"pedido_id": pedido["id"], "latencia_creacion": latencia, "t_creado": time.perf_counter()}


def esperar_entrega(pedido_id: int) -> dict:
    t_inicio = time.perf_counter()
    while time.perf_counter() - t_inicio < POLL_TIMEOUT:
        resp = requests.get(f"{GATEWAY_URL}/pedidos/{pedido_id}", timeout=10)
        resp.raise_for_status()
        pedido = resp.json()
        if pedido["estado"] == "ENTREGADO":
            return {"pedido_id": pedido_id, "t_entregado": time.perf_counter(), "ok": True}
        time.sleep(POLL_INTERVAL)
    return {"pedido_id": pedido_id, "t_entregado": None, "ok": False}


def correr_nivel(n: int) -> dict:
    print(f"\n=== Nivel de carga: {n} pedidos concurrentes ===")
    t_inicio_total = time.perf_counter()

    # 1) Disparar los N pedidos concurrentemente (mide latencia de creación,
    #    que es la percibida por el cliente al hacer clic en "Confirmar pedido").
    creaciones = []
    with ThreadPoolExecutor(max_workers=n) as executor:
        futuros = [executor.submit(crear_pedido, i) for i in range(n)]
        for f in as_completed(futuros):
            creaciones.append(f.result())

    t_fin_creacion = time.perf_counter()
    latencias_creacion = [c["latencia_creacion"] for c in creaciones]

    # 2) Esperar (poll) hasta que todos alcancen ENTREGADO: mide el tiempo de
    #    procesamiento distribuido de punta a punta, gobernado por los
    #    ThreadPoolExecutor de Kitchen y Dispatch.
    ids = [c["pedido_id"] for c in creaciones]
    entregas = []
    with ThreadPoolExecutor(max_workers=n) as executor:
        futuros = [executor.submit(esperar_entrega, pid) for pid in ids]
        for f in as_completed(futuros):
            entregas.append(f.result())

    t_fin_total = time.perf_counter()
    exitosos = [e for e in entregas if e["ok"]]
    fallidos = n - len(exitosos)
    duracion_total = t_fin_total - t_inicio_total

    resultado = {
        "n": n,
        "duracion_creacion_s": round(t_fin_creacion - t_inicio_total, 3),
        "duracion_total_s": round(duracion_total, 3),
        "pedidos_entregados": len(exitosos),
        "pedidos_fallidos": fallidos,
        "throughput_pedidos_por_s": round(len(exitosos) / duracion_total, 3) if duracion_total > 0 else 0,
        "latencia_creacion_ms": {
            "min": round(min(latencias_creacion) * 1000, 2),
            "avg": round(statistics.mean(latencias_creacion) * 1000, 2),
            "p95": round(statistics.quantiles(latencias_creacion, n=20)[18] * 1000, 2) if n >= 20 else round(max(latencias_creacion) * 1000, 2),
            "max": round(max(latencias_creacion) * 1000, 2),
        },
    }

    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return resultado


def main():
    parser = argparse.ArgumentParser(description="Prueba de carga Café Express Distribuido")
    parser.add_argument("--niveles", type=int, nargs="+", default=[10, 25, 50, 100])
    parser.add_argument("--salida", type=str, default=None)
    args = parser.parse_args()

    try:
        requests.get(f"{GATEWAY_URL}/health", timeout=5).raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"No se pudo contactar al Gateway en {GATEWAY_URL}: {exc}")

    resultados = [correr_nivel(n) for n in args.niveles]

    print("\n=== Resumen ===")
    print(f"{'N':>6} | {'Entregados':>10} | {'Fallidos':>8} | {'Total (s)':>10} | {'Throughput (p/s)':>16} | {'Lat. creación p95 (ms)':>22}")
    for r in resultados:
        print(
            f"{r['n']:>6} | {r['pedidos_entregados']:>10} | {r['pedidos_fallidos']:>8} | "
            f"{r['duracion_total_s']:>10} | {r['throughput_pedidos_por_s']:>16} | {r['latencia_creacion_ms']['p95']:>22}"
        )

    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        print(f"\nResultados guardados en {args.salida}")


if __name__ == "__main__":
    main()
