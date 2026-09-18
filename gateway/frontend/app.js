const MENU = [
  { producto: "Café", precio_unitario: 3500 },
  { producto: "Pizza", precio_unitario: 18000 },
  { producto: "Hamburguesa", precio_unitario: 15000 },
  { producto: "Jugo", precio_unitario: 5000 },
];

const STATES = ["CREADO", "EN_PREPARACION", "LISTO", "EN_DESPACHO", "ENTREGADO"];
const MAX_CARDS = 20;
const POLL_MS = 1200;

const qty = {};
MENU.forEach((item) => { qty[item.producto] = 0; });

const menuEl = document.getElementById("menu");
const totalDisplay = document.getElementById("totalDisplay");
const confirmarBtn = document.getElementById("confirmarBtn");
const orderError = document.getElementById("orderError");
const clienteInput = document.getElementById("clienteInput");
const pedidosList = document.getElementById("pedidosList");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

function money(n) {
  return "$" + Math.round(n).toLocaleString("es-CO");
}

function renderMenu() {
  menuEl.innerHTML = "";
  MENU.forEach((item) => {
    const row = document.createElement("div");
    row.className = "menu-item";
    row.innerHTML = `
      <div class="menu-item-info">
        <span class="menu-item-name">${item.producto}</span>
        <span class="menu-item-price">${money(item.precio_unitario)}</span>
      </div>
      <div class="qty-control">
        <button class="qty-btn" data-action="dec" data-producto="${item.producto}">−</button>
        <span class="qty-value" id="qty-${item.producto}">${qty[item.producto]}</span>
        <button class="qty-btn" data-action="inc" data-producto="${item.producto}">+</button>
      </div>
    `;
    menuEl.appendChild(row);
  });
}

function updateTotal() {
  const total = MENU.reduce((acc, item) => acc + qty[item.producto] * item.precio_unitario, 0);
  totalDisplay.textContent = money(total);
  confirmarBtn.disabled = total <= 0;
}

menuEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".qty-btn");
  if (!btn) return;
  const producto = btn.dataset.producto;
  if (btn.dataset.action === "inc") qty[producto] += 1;
  else qty[producto] = Math.max(0, qty[producto] - 1);
  document.getElementById(`qty-${producto}`).textContent = qty[producto];
  updateTotal();
});

confirmarBtn.addEventListener("click", async () => {
  orderError.textContent = "";
  const items = MENU
    .filter((item) => qty[item.producto] > 0)
    .map((item) => ({ producto: item.producto, cantidad: qty[item.producto], precio_unitario: item.precio_unitario }));

  if (items.length === 0) return;

  confirmarBtn.disabled = true;
  confirmarBtn.textContent = "Enviando…";

  try {
    const resp = await fetch("/pedidos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cliente: clienteInput.value || "Cliente", items }),
    });
    if (!resp.ok) throw new Error(`El servidor respondió ${resp.status}`);

    MENU.forEach((item) => { qty[item.producto] = 0; });
    renderMenu();
    updateTotal();
    fetchPedidos();
  } catch (err) {
    orderError.textContent = "No se pudo crear el pedido: " + err.message + ". ¿Están corriendo los 6 servicios?";
  } finally {
    confirmarBtn.textContent = "Confirmar pedido";
    updateTotal();
  }
});

function stepIndex(estado) {
  return STATES.indexOf(estado);
}

function pedidoBodyHTML(pedido) {
  const idx = stepIndex(pedido.estado);
  const isCancelado = pedido.estado === "CANCELADO";

  let trackerHTML = "";
  let labelsHTML = "";
  if (!isCancelado) {
    trackerHTML = STATES.map((_, i) => {
      const cls = i < idx ? "done" : i === idx ? "current" : "";
      return `<div class="tracker-step ${cls}"></div>`;
    }).join("");
    labelsHTML = STATES.map((s, i) => {
      const cls = i < idx ? "past" : i === idx ? "active" : "";
      return `<span class="${cls}">${s.replace("EN_", "")}</span>`;
    }).join("");
  }

  const entregado = pedido.estado === "ENTREGADO"
    ? `<div class="badge-entregado">✓ Entregado</div>`
    : "";
  const cancelado = isCancelado
    ? `<div class="pedido-meta" style="color:#C23B3B;font-weight:700;">Pedido cancelado</div>`
    : "";

  return `
    <div class="pedido-head">
      <div>
        <span class="pedido-id">#${pedido.id}</span>
        <span class="pedido-cliente"> · ${pedido.cliente}</span>
      </div>
      <span class="pedido-total">${money(pedido.total)}</span>
    </div>
    ${!isCancelado ? `<div class="tracker">${trackerHTML}</div><div class="tracker-labels">${labelsHTML}</div>` : ""}
    ${entregado}${cancelado}
    <div class="pedido-meta">${pedido.items.map((i) => `${i.cantidad}× ${i.producto}`).join(", ")}</div>
  `;
}

// Mapa id -> elemento DOM ya insertado. Actualizar el contenido de una
// tarjeta existente (en vez de destruirla y recrearla en cada poll) evita
// que la animación de entrada se repita y el pedido "parpadee" mientras
// avanza de estado cada 1.2s.
const cardElements = new Map();
let fetchInFlight = false;

function renderPedidos(pedidos) {
  if (pedidos.length === 0) {
    pedidosList.innerHTML = `<p class="empty-state">Todavía no hay pedidos. Crea el primero a la izquierda.</p>`;
    cardElements.clear();
    return;
  }

  const ordenados = [...pedidos].sort((a, b) => b.id - a.id).slice(0, MAX_CARDS);
  const idsVisibles = new Set(ordenados.map((p) => p.id));

  // limpiar el mensaje de "sin pedidos" si estaba presente
  const empty = pedidosList.querySelector(".empty-state");
  if (empty) pedidosList.innerHTML = "";

  let prevEl = null;
  ordenados.forEach((pedido) => {
    let el = cardElements.get(pedido.id);
    if (!el) {
      el = document.createElement("div");
      el.className = "pedido-card";
      el.dataset.id = pedido.id;
      cardElements.set(pedido.id, el);
    }
    if (el.dataset.estado !== pedido.estado) {
      el.innerHTML = pedidoBodyHTML(pedido);
      el.dataset.estado = pedido.estado;
    }
    // mantener el orden correcto (más recientes primero) sin recrear nodos
    if (prevEl === null) {
      if (pedidosList.firstChild !== el) pedidosList.insertBefore(el, pedidosList.firstChild);
    } else if (prevEl.nextSibling !== el) {
      prevEl.after(el);
    }
    prevEl = el;
  });

  // remover tarjetas de pedidos que ya no están en los últimos MAX_CARDS
  for (const [id, el] of cardElements) {
    if (!idsVisibles.has(id)) {
      el.remove();
      cardElements.delete(id);
    }
  }
}

async function fetchPedidos() {
  if (fetchInFlight) return;
  fetchInFlight = true;
  try {
    const resp = await fetch("/pedidos");
    if (!resp.ok) throw new Error("status " + resp.status);
    const pedidos = await resp.json();
    statusDot.className = "dot ok";
    statusText.textContent = "Sistema en línea";
    renderPedidos(pedidos);
  } catch (err) {
    statusDot.className = "dot err";
    statusText.textContent = "Sin conexión al Gateway";
  } finally {
    fetchInFlight = false;
  }
}

renderMenu();
updateTotal();
fetchPedidos();
setInterval(fetchPedidos, POLL_MS);
