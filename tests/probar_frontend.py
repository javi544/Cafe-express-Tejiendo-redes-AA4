"""Prueba visual e interactiva del frontend del Gateway: abre la página,
agrega productos al carrito, confirma dos pedidos y verifica que las
tarjetas avanzan de estado sin parpadear entre actualizaciones."""
from playwright.sync_api import sync_playwright

OUT = "/home/claude/cafe-distribuido/proyecto/docs/evidencias"


def confirmar_pedido(page, cafes, pizzas):
    if cafes:
        btn = page.locator('.qty-btn[data-producto="Café"][data-action="inc"]')
        for _ in range(cafes):
            btn.click()
    if pizzas:
        btn = page.locator('.qty-btn[data-producto="Pizza"][data-action="inc"]')
        for _ in range(pizzas):
            btn.click()
    page.locator("#confirmarBtn").click()
    page.wait_for_timeout(300)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    page = browser.new_page(viewport={"width": 1400, "height": 950})
    page.goto("http://localhost:8000/", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(400)

    confirmar_pedido(page, cafes=2, pizzas=1)
    page.wait_for_timeout(600)
    confirmar_pedido(page, cafes=1, pizzas=0)

    # Dos capturas muy seguidas (400ms) durante el procesamiento, para
    # comprobar que la tarjeta NO se desvanece/parpadea entre polls.
    page.wait_for_timeout(1200)
    page.screenshot(path=f"{OUT}/frontend_multi_a.png")
    page.wait_for_timeout(400)
    page.screenshot(path=f"{OUT}/frontend_multi_b.png")
    print("capturas: frontend_multi_a.png, frontend_multi_b.png")

    # Esperar a que ambos pedidos queden entregados
    page.wait_for_timeout(3500)
    page.screenshot(path=f"{OUT}/frontend_multi_entregados.png")
    print("captura: frontend_multi_entregados.png")

    browser.close()
