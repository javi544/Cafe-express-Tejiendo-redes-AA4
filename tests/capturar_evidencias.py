"""Captura evidencias visuales del sistema distribuido en funcionamiento."""
from playwright.sync_api import sync_playwright

PAGES = [
    ("http://localhost:8000/docs", "gateway_swagger.png"),
    ("http://localhost:8002/eventos", "mediator_eventos.png"),
    ("http://localhost:8005/notificaciones", "notifications_observer.png"),
    ("http://localhost:8001/pedidos", "orders_listado.png"),
]

OUT_DIR = "/home/claude/cafe-distribuido/proyecto/docs/evidencias"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    for url, filename in PAGES:
        page.goto(url, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(500)
        page.screenshot(path=f"{OUT_DIR}/{filename}")
        print(f"guardado: {filename}")
    browser.close()
