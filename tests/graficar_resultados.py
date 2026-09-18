"""Genera gráficas de la prueba de carga a partir de resultados_carga.json (5 workers)
y resultados_carga_100_20workers.json (comparación con 20 workers)."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/home/claude/cafe-distribuido/proyecto/docs/evidencias"

with open(f"{BASE}/resultados_carga.json", encoding="utf-8") as f:
    datos = json.load(f)

with open(f"{BASE}/resultados_carga_100_20workers.json", encoding="utf-8") as f:
    datos_20w = json.load(f)[0]

ns = [d["n"] for d in datos]
throughput = [d["throughput_pedidos_por_s"] for d in datos]
duracion = [d["duracion_total_s"] for d in datos]
p95 = [d["latencia_creacion_ms"]["p95"] for d in datos]

TEAL = "#065A82"
NAVY = "#21295C"
LIGHT = "#1C7293"

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

axes[0].bar([str(n) for n in ns], throughput, color=TEAL)
axes[0].set_title("Throughput de entrega vs. pedidos concurrentes\n(Kitchen/Dispatch: 5 hilos)")
axes[0].set_xlabel("Pedidos concurrentes (N)")
axes[0].set_ylabel("Pedidos entregados / segundo")
for i, v in enumerate(throughput):
    axes[0].text(i, v + 0.08, f"{v:.2f}", ha="center", fontsize=9)

axes[1].bar([str(n) for n in ns], p95, color=NAVY)
axes[1].set_title("Latencia de creación del pedido (p95)\n(percibida por el cliente)")
axes[1].set_xlabel("Pedidos concurrentes (N)")
axes[1].set_ylabel("Milisegundos")
for i, v in enumerate(p95):
    axes[1].text(i, v + 8, f"{v:.0f}", ha="center", fontsize=9)

fig.tight_layout()
fig.savefig(f"{BASE}/grafica_throughput_latencia.png", dpi=150)
print("guardado: grafica_throughput_latencia.png")

# Comparación 5 vs 20 hilos a N=100
fig2, ax = plt.subplots(figsize=(5.5, 4.2))
etiquetas = ["5 hilos\n(Kitchen+Dispatch)", "20 hilos\n(Kitchen+Dispatch)"]
valores = [next(d for d in datos if d["n"] == 100)["throughput_pedidos_por_s"], datos_20w["throughput_pedidos_por_s"]]
colores = [TEAL, LIGHT]
ax.bar(etiquetas, valores, color=colores)
ax.set_title("Escalabilidad horizontal a N=100 pedidos\n(mismo código, más hilos por servicio)")
ax.set_ylabel("Pedidos entregados / segundo")
for i, v in enumerate(valores):
    ax.text(i, v + 0.15, f"{v:.2f} p/s", ha="center", fontsize=10)
fig2.tight_layout()
fig2.savefig(f"{BASE}/grafica_escalabilidad.png", dpi=150)
print("guardado: grafica_escalabilidad.png")
