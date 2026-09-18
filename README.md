# ☕ Café Express Distribuido — Arquitectura de Microservicios

Prototipo funcional desarrollado como parte del mini proyecto de la Unidad 2, *"Tejiendo redes: arquitectura de software entre hilos y nodos"*. Evoluciona el sistema monolítico de la Actividad 2 hacia una arquitectura de **seis microservicios independientes**, coordinados mediante los patrones **Proxy**, **Mediator** y **Observer**, con concurrencia real basada en `ThreadPoolExecutor`. Incluye un frontend web servido por el Gateway (`http://localhost:8000/`) para crear pedidos y ver en vivo cómo avanzan por el sistema.

> El informe técnico completo (PDF, con diagramas UML, justificación de patrones y resultados de pruebas de carga) y la presentación en video se entregan por separado en el LMS. Este repositorio contiene únicamente el código fuente del prototipo.

## Arquitectura

| Servicio | Puerto | Patrón / Rol | Responsabilidad |
|---|---|---|---|
| `gateway` | 8000 | **Proxy** (único puerto público) | Punto único de entrada; reenvía las solicitudes del cliente a Orders |
| `orders` | 8001 | Fuente de verdad | Crea y persiste pedidos (SQLite); valida transiciones de estado; publica eventos al Mediator |
| `mediator` | 8002 | **Mediator** | Único servicio que conoce a Kitchen, Dispatch y Notifications; enruta cada evento |
| `kitchen` | 8003 | Worker concurrente | Simula la preparación del pedido en un hilo de un `ThreadPoolExecutor` |
| `dispatch` | 8004 | Worker concurrente | Simula el despacho/entrega del pedido en un hilo de un `ThreadPoolExecutor` |
| `notifications` | 8005 | **Observer** | Se suscribe a todos los eventos y genera el mensaje para el cliente |

```
Cliente → Gateway (Proxy) → Orders ──eventos──▶ Mediator ──▶ Kitchen / Dispatch (ThreadPoolExecutor)
                                                        └──▶ Notifications (Observer, todos los eventos)
```

Orders **nunca** conoce a Kitchen, Dispatch ni Notifications: solo publica eventos al Mediator, que decide a quién reenviarlos. Esto permite agregar nuevos servicios reactivos sin tocar el resto del sistema.

## Estructura del proyecto

```
cafe-express-distribuido/
├── gateway/            # Proxy — único servicio con puerto público
│   └── frontend/         # Interfaz web (HTML/CSS/JS) servida como estáticos por el Gateway
├── orders/             # Fuente de verdad del pedido (SQLite)
├── mediator/           # Enrutamiento de eventos
├── kitchen/             # Preparación (ThreadPoolExecutor)
├── dispatch/            # Despacho (ThreadPoolExecutor)
├── notifications/       # Observer — notificaciones al cliente
├── diagramas/            # UML: componentes, secuencia, despliegue (.puml + .png)
├── tests/
│   └── load_test.py       # Script de prueba de carga (10/25/50/100 pedidos concurrentes)
├── docker-compose.yml
└── README.md
```

Cada servicio es independiente: su propio `app/`, `requirements.txt` y `Dockerfile`.

## Ciclo de vida de un pedido

```
CREADO → EN_PREPARACION → LISTO → EN_DESPACHO → ENTREGADO
```

Cada cambio de estado lo reporta el servicio correspondiente (Kitchen o Dispatch) a Orders vía `PATCH`, y Orders vuelve a publicar el evento al Mediator, que lo reenvía a quien deba reaccionar. `CANCELADO` también existe como transición manual desde `CREADO` o `EN_PREPARACION`.

## Instalación y ejecución

### Opción A — Docker Compose (recomendada)

```bash
docker compose up --build
```

Solo el Gateway publica un puerto al host. Todo el sistema se usa a través de él:

- **Frontend web**: `http://localhost:8000/` — interfaz para crear pedidos y ver su avance en vivo (se actualiza sola cada 1.2s), sin necesidad de curl ni Swagger.
- Crear pedido: `POST http://localhost:8000/pedidos`
- Consultar pedido: `GET http://localhost:8000/pedidos/{id}`
- Listar pedidos: `GET http://localhost:8000/pedidos`
- Documentación interactiva: `http://localhost:8000/docs`

> **Nota:** el Gateway sirve el frontend como archivos estáticos empaquetados dentro de su propia imagen (`gateway/frontend/`). Si ya habías construido las imágenes de Docker antes, es necesario reconstruirlas con `docker compose up --build` (no basta con `docker compose up`) para que el contenedor incluya los archivos del frontend.

### Opción B — Local (Python, un servicio por proceso)

Cada servicio es una app FastAPI independiente. Se puede levantar todo el sistema en la misma máquina usando puertos distintos (útil para probar sin Docker):

```bash
python3 -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic requests

# En 6 terminales distintas (o en segundo plano):
(cd orders        && uvicorn app.main:app --port 8001)
(cd mediator      && uvicorn app.main:app --port 8002)
(cd kitchen       && uvicorn app.main:app --port 8003)
(cd dispatch      && uvicorn app.main:app --port 8004)
(cd notifications && uvicorn app.main:app --port 8005)
(cd gateway       && uvicorn app.main:app --port 8000)
```

Las URLs por defecto de cada servicio ya apuntan a `localhost` en el puerto correspondiente, así que no se necesita configurar variables de entorno para probar en local. En Docker Compose, `docker-compose.yml` las sobreescribe con los nombres de servicio de la red interna (p. ej. `http://orders:8001`).

### Probar el ciclo completo

```bash
curl -X POST http://localhost:8000/pedidos -H "Content-Type: application/json" -d '{
  "cliente": "Javier",
  "items": [{"producto": "Café", "cantidad": 2, "precio_unitario": 3500}]
}'
# Esperar unos segundos y consultar:
curl http://localhost:8000/pedidos/1
```

El pedido debe recorrer automáticamente `CREADO → EN_PREPARACION → LISTO → EN_DESPACHO → ENTREGADO` sin más intervención del cliente.

## Prueba de carga

```bash
source .venv/bin/activate
pip install requests
python tests/load_test.py --niveles 10 25 50 100 --salida resultados.json
```

Dispara N pedidos concurrentes contra el Gateway y mide, para cada nivel: latencia de creación del pedido, duración total hasta que todos quedan `ENTREGADO`, y throughput (pedidos entregados/segundo). El script requiere que los 6 servicios estén corriendo (local o Docker).

### Resultados reales obtenidos (5 hilos por servicio en Kitchen/Dispatch)

| N concurrentes | Entregados / Fallidos | Duración total (s) | Throughput (pedidos/s) | Latencia creación p95 (ms) |
|---|---|---|---|---|
| 10 | 10 / 0 | 3.99 | 2.51 | 157 |
| 25 | 25 / 0 | 7.16 | 3.49 | 546 |
| 50 | 50 / 0 | 13.27 | 3.77 | 636 |
| 100 | 100 / 0 | 23.69 | 4.22 | 808 |

**0% de pedidos fallidos en los cuatro niveles.** Al aumentar `MAX_WORKERS` de 5 a 20 en Kitchen y Dispatch (sin cambiar código), el throughput a 100 pedidos concurrentes pasó de **4.22 a 10.45 pedidos/segundo** (≈2.5×), confirmando que el sistema escala horizontalmente por configuración. Detalle completo, gráficas y análisis en el informe técnico (PDF) entregado en el LMS.

## Diagramas UML

Fuente `.puml` y renders `.png` en `diagramas/`:

- **Componentes**: vista general de los seis servicios y sus dependencias.
- **Secuencia**: ciclo de vida distribuido de un pedido, de principio a fin.
- **Despliegue**: contenedores Docker, puertos internos y el único puerto publicado al host.

## Estrategia de commits

Se sigue la convención **Conventional Commits**:

| Prefijo | Uso |
|---|---|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección de errores |
| `docs:` | Cambios en documentación |
| `refactor:` | Cambios internos sin alterar comportamiento |
| `chore:` | Mantenimiento (configuración, dependencias) |

## Video de sustentación

📺 Video (YouTube, no listado): **https://youtu.be/pUdx2tp3b0o**

## Autor

Javier Trujillo — Mini proyecto Unidad 2, "Tejiendo redes: arquitectura de software entre hilos y nodos" (Arquitectura de Software).
