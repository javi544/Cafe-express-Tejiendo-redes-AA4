"""Captura la vista de un único pedido con su historial completo, como evidencia legible."""
from playwright.sync_api import sync_playwright

OUT_DIR = "/home/claude/cafe-distribuido/proyecto/docs/evidencias"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    page = browser.new_page(viewport={"width": 900, "height": 500})
    page.goto("http://localhost:8000/pedidos/1", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(300)
    page.screenshot(path=f"{OUT_DIR}/pedido_ciclo_completo.png")
    browser.close()
    print("guardado: pedido_ciclo_completo.png")
