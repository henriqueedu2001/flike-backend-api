import base64
from io import BytesIO
import os
from pathlib import Path
import re
import struct
import uuid

import httpx
from PIL import Image
from playwright.sync_api import expect, sync_playwright
import pytest
import zxingcpp

WEB = os.environ.get("E2E_WEB_URL", "http://127.0.0.1:3001")
API = os.environ.get("E2E_API_URL", "http://127.0.0.1:18001")
PASSWORD = "Demo-Browser-123!"
ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "e2e"


@pytest.fixture(scope="module")
def browser():
    assert os.getenv("DB_DATABASE") == "flike_test", "Browser tests require the isolated database"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


def register_and_login(page, name, email):
    page.goto(WEB + "/signup")
    page.get_by_label("Nome", exact=True).fill(name)
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Senha", exact=True).fill(PASSWORD)
    page.get_by_label(re.compile("Confirmar [Ss]enha")).fill(PASSWORD)
    page.get_by_role("button", name=re.compile("Criar [Cc]onta")).click()
    expect(page).to_have_url(re.compile(r"/login\?created=1$"))
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Senha", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    expect(page).to_have_url(re.compile(r"/dashboard$"))
    expect(page.get_by_role("heading", name="Meu painel")).to_be_visible()


def create_hierarchy(page, marker):
    names = {"institution": f"Instituição E2E {marker}", "building": f"Edifício E2E {marker}", "room": f"Sala E2E {marker}"}
    page.goto(WEB + "/admin/dashboard")
    page.get_by_role("button", name="+ Nova Instituição", exact=True).click()
    modal = page.get_by_role("dialog")
    modal.get_by_label("Nome", exact=True).fill(names["institution"])
    modal.get_by_role("button", name="Salvar", exact=True).click()
    expect(modal).not_to_be_visible()
    expect(page.get_by_text(names["institution"], exact=True)).to_be_visible()
    page.get_by_role("button", name="+ Novo Prédio", exact=True).click()
    modal.get_by_placeholder("Buscar instituição...").fill(names["institution"])
    modal.get_by_text(names["institution"], exact=True).click()
    for field, value in {"Nome": names["building"], "Endereço": "Rua de teste", "Complemento": "Bloco A", "Cidade": "São Paulo", "Estado": "SP", "CEP": "01000-000", "País": "Brasil"}.items():
        modal.get_by_label(re.compile(r"^Complemento") if field == "Complemento" else field, exact=field != "Complemento").fill(value)
    modal.get_by_role("button", name="Salvar", exact=True).click()
    expect(modal).not_to_be_visible()
    page.get_by_role("button", name="+ Nova Sala", exact=True).click()
    modal.get_by_placeholder("Buscar prédio...").fill(names["building"])
    modal.get_by_text(names["building"], exact=True).click()
    modal.get_by_label("Nome", exact=True).fill(names["room"])
    modal.get_by_label("Número", exact=True).fill("101")
    modal.get_by_role("button", name="Salvar", exact=True).click()
    expect(modal).not_to_be_visible()
    page.get_by_role("button", name="+ Nova Fechadura", exact=True).click()
    modal.get_by_placeholder("Buscar sala...").fill(names["room"])
    modal.get_by_text(names["room"], exact=True).click()
    modal.get_by_role("button", name="Salvar", exact=True).click()
    expect(modal).not_to_be_visible()
    expect(page.get_by_text("Chave Secreta", exact=True)).to_have_count(0)
    return names


def request_key(page, names):
    page.goto(WEB + "/access/request")
    page.get_by_placeholder("Buscar instituição...").fill(names["institution"])
    page.get_by_text(names["institution"], exact=True).click()
    page.get_by_placeholder("Buscar prédio...").fill(names["building"])
    page.get_by_text(names["building"], exact=True).click()
    page.get_by_placeholder("Buscar sala...").fill(names["room"])
    page.get_by_text(names["room"], exact=True).click()
    page.get_by_role("button", name=re.compile("Solicitar [Cc]have")).click()
    page.get_by_role("link", name="Acompanhar solicitação", exact=True).click()
    expect(page).to_have_url(re.compile(r"/dashboard$"), timeout=15000)
    expect(page.get_by_text("Pendente", exact=True)).to_be_visible()


@pytest.mark.parametrize("viewport", [{"width": 1366, "height": 900}, {"width": 390, "height": 844}], ids=["desktop", "mobile"])
def test_full_demo_on_real_api(browser, viewport):
    marker = uuid.uuid4().hex[:8]
    device = "mobile" if viewport["width"] < 600 else "desktop"
    owner_context = browser.new_context(viewport=viewport)
    visitor_context = browser.new_context(viewport=viewport)
    owner, visitor = owner_context.new_page(), visitor_context.new_page()
    errors = []
    owner.on("pageerror", lambda error: errors.append(str(error)))
    visitor.on("pageerror", lambda error: errors.append(str(error)))
    try:
        owner_email, visitor_email = f"browser-owner-{marker}@example.com", f"browser-visitor-{marker}@example.com"
        register_and_login(owner, "Responsável " + marker, owner_email)
        names = create_hierarchy(owner, marker)
        register_and_login(visitor, "Solicitante " + marker, visitor_email)
        request_key(visitor, names)
        owner.goto(WEB + "/admin/keys")
        owner.get_by_label("Validade da chave (minutos)", exact=True).fill("1")
        row = owner.get_by_role("row").filter(has_text=visitor_email)
        expect(row).to_contain_text("Pendente")
        with owner.expect_response(lambda response: "/approve" in response.url and response.request.method == "POST") as decision:
            row.get_by_role("button", name="Aprovar", exact=True).click()
        assert decision.value.status == 200
        key_id = decision.value.json()["digital_key_id"]
        visitor.reload()
        expect(visitor.get_by_text("Aprovada", exact=True)).to_be_visible()
        visitor.get_by_role("link", name="Ver QR Code", exact=True).first.click()
        expect(visitor).to_have_url(WEB + f"/access/{key_id}")
        qr = visitor.get_by_role("img", name=re.compile("QR"))
        expect(qr).to_be_visible()
        source = qr.get_attribute("src")
        decoded = zxingcpp.read_barcode(Image.open(BytesIO(base64.b64decode(source.split(",", 1)[1]))))
        assert decoded is not None
        token = visitor.evaluate("localStorage.getItem('access_token')")
        key_response = httpx.get(API + f"/digital_key?key_id={key_id}", headers={"Authorization": "Bearer " + token})
        assert key_response.status_code == 200
        assert decoded.bytes == bytes.fromhex(key_response.json()["payload"])
        assert len(decoded.bytes) == 48
        assert struct.unpack(">QQQQ", decoded.bytes[:32])[2] < struct.unpack(">QQQQ", decoded.bytes[:32])[3]
        visitor.reload()
        expect(qr).to_be_visible()
        assert qr.get_attribute("src") == source
        visitor.screenshot(path=str(ARTIFACTS / f"{device}-qr.png"), full_page=True)
        assert visitor.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        request_key(visitor, names)
        owner.reload()
        row = owner.get_by_role("row").filter(has_text=visitor_email).filter(has=owner.get_by_role("button", name="Rejeitar", exact=True))
        owner.once("dialog", lambda dialog: dialog.accept())
        row.get_by_role("button", name="Rejeitar", exact=True).click()
        owner.get_by_role("button", name="Rejeitadas", exact=True).click()
        expect(owner.get_by_text("Rejeitada", exact=True)).to_be_visible()
        visitor.reload()
        expect(visitor.get_by_text("Rejeitada", exact=True)).to_be_visible()
        expect(visitor.get_by_text("Aprovada", exact=True)).to_be_visible()
        visitor.screenshot(path=str(ARTIFACTS / f"{device}-dashboard.png"), full_page=True)
        assert visitor.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        owner.goto(WEB + "/users")
        holder = owner.get_by_role("row").filter(has_text=visitor_email)
        holder.get_by_role("link").click()
        expect(owner.get_by_role("heading", name=re.compile("[Ee]miss|[Aa]utoriza"))).to_be_visible()
        expect(owner.get_by_text("Usada em", exact=True)).to_have_count(0)
        # The same authorization is available after leaving and re-authenticating.
        visitor.get_by_role("button", name="Sair", exact=True).click()
        expect(visitor).to_have_url(re.compile(r"/login"))
        visitor.get_by_label("Email", exact=True).fill(visitor_email)
        visitor.get_by_label("Senha", exact=True).fill(PASSWORD)
        visitor.get_by_role("button", name="Entrar", exact=True).click()
        expect(visitor.get_by_text("Aprovada", exact=True)).to_be_visible()
        # Advance only the browser clock to exercise the live expiry presentation.
        visitor.clock.install()
        visitor.goto(WEB + f"/access/{key_id}")
        expect(visitor.get_by_role("img", name=re.compile("QR"))).to_be_visible()
        visitor.clock.fast_forward(61000)
        expect(visitor.get_by_text("Status: Expirada", exact=True)).to_be_visible()
        expect(visitor.get_by_role("img", name=re.compile("QR"))).to_have_count(0)
        visitor.screenshot(path=str(ARTIFACTS / f"{device}-expired.png"), full_page=True)
        assert not errors, errors
    finally:
        owner_context.close()
        visitor_context.close()


def test_session_and_network_failure_feedback(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        page.goto(WEB + "/dashboard")
        expect(page).to_have_url(re.compile(r"/login"))
        marker = uuid.uuid4().hex[:8]
        email = f"browser-session-{marker}@example.com"
        register_and_login(page, "Sessão teste", email)
        page.evaluate("localStorage.setItem('access_token', 'expired-invalid-token')")
        page.reload()
        expect(page).to_have_url(re.compile(r"/login"))
        expect(page.get_by_text(re.compile("[Ss]essão.*expir"))).to_be_visible()
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Senha", exact=True).fill("Senha-incorreta-123")
        page.get_by_role("button", name="Entrar", exact=True).click()
        expect(page.get_by_role("alert").filter(has_text=re.compile(".+"))).to_be_visible()
        page.get_by_label("Senha", exact=True).fill(PASSWORD)
        page.get_by_role("button", name="Entrar", exact=True).click()
        expect(page).to_have_url(re.compile(r"/dashboard$"))
        # Only this failure case interrupts network; the complete demo above uses real services.
        page.route(API + "/**", lambda route: route.abort("connectionrefused"))
        page.reload()
        expect(page.get_by_role("alert").filter(has_text=re.compile("conexão|conectar|comunicar|indisponível", re.I))).to_be_visible()
        page.unroute(API + "/**")
        page.get_by_role("button", name="Tentar novamente", exact=True).click()
        expect(page.get_by_role("heading", name="Minhas solicitações")).to_be_visible()
    finally:
        context.close()
