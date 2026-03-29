from pathlib import Path
import re
import unicodedata

import pdfplumber
from playwright.sync_api import sync_playwright

URL = "https://erpsol.valurq.com.py/#"
USUARIO = "diego"
CLAVE = "Arce556965?"
ARCHIVO_FACTURAS = "facturas.txt"
CARPETA_DESCARGAS = "/Users/diegosoljancic/Downloads"


def debug(msg: str):
    print(msg, flush=True)


def leer_facturas_txt(ruta_txt: str) -> list[str]:
    path = Path(ruta_txt)

    if not path.exists():
        raise FileNotFoundError(f"No encontré el archivo: {ruta_txt}")

    facturas = []
    for linea in path.read_text(encoding="utf-8").splitlines():
        valor = linea.strip()
        if not valor:
            continue
        facturas.append(valor)

    if not facturas:
        raise ValueError("El archivo TXT está vacío.")

    return facturas


def escribir_input(locator, valor: str):
    locator.click()
    try:
        locator.press("Control+A")
    except Exception:
        pass
    try:
        locator.press("Meta+A")
    except Exception:
        pass
    locator.fill("")
    locator.type(str(valor), delay=40)


def sigue_en_login(page) -> bool:
    try:
        if page.locator('input[name="usuario"]').first.is_visible(timeout=500):
            return True
    except Exception:
        pass

    try:
        if page.locator('input[name="clave"]').first.is_visible(timeout=500):
            return True
    except Exception:
        pass

    try:
        body = page.locator("body").inner_text(timeout=1500).lower()
        if "iniciar sesión" in body or "iniciar sesion" in body:
            return True
        if "usuario" in body and "password" in body:
            return True
    except Exception:
        pass

    return False


def login_exitoso(page) -> bool:
    if sigue_en_login(page):
        return False

    try:
        body = page.locator("body").inner_text(timeout=2000)

        señales_ok = [
            "SISTEMA DE GESTION Y ADMINISTRACION",
            "PANEL DE FACTURACIÓN",
            "PANEL DE FACTURACION",
            "VENTAS",
            "FICHA DE PRODUCTOS",
        ]

        return any(s in body for s in señales_ok)
    except Exception:
        return False


def click_boton_ingresar(page) -> bool:
    candidatos = [
        'button:has-text("INGRESAR")',
        'button:has-text("Ingresar")',
        'text=INGRESAR',
        'text=Ingresar',
        'button[type="submit"]',
    ]

    for sel in candidatos:
        try:
            btn = page.locator(sel).first
            if btn.count() == 0:
                continue

            try:
                btn.wait_for(state="visible", timeout=1000)
            except Exception:
                continue

            try:
                btn.click(timeout=2000)
                return True
            except Exception:
                pass

            try:
                btn.click(force=True, timeout=2000)
                return True
            except Exception:
                pass

            try:
                btn.evaluate("el => el.click()")
                return True
            except Exception:
                pass

        except Exception:
            continue

    return False


def hacer_login(page, intentos=18):
    debug("Abriendo ERP...")

    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2500)

    page.locator('input[name="usuario"]').first.wait_for(state="visible", timeout=15000)
    page.locator('input[name="clave"]').first.wait_for(state="visible", timeout=15000)

    usuario = page.locator('input[name="usuario"]').first
    clave = page.locator('input[name="clave"]').first

    escribir_input(usuario, USUARIO)
    escribir_input(clave, CLAVE)

    for i in range(1, intentos + 1):
        debug(f"Intento login {i}")

        if login_exitoso(page):
            debug("Login correcto")
            return

        ok_click = click_boton_ingresar(page)

        if not ok_click:
            debug("No pude clicar bien INGRESAR, probando Enter...")
            try:
                clave.press("Enter")
            except Exception:
                pass

        page.wait_for_timeout(1600)

        if login_exitoso(page):
            debug("Login correcto")
            return

        if i % 4 == 0 and sigue_en_login(page):
            debug("Reescribiendo credenciales por las dudas...")
            try:
                escribir_input(usuario, USUARIO)
            except Exception:
                pass
            try:
                escribir_input(clave, CLAVE)
            except Exception:
                pass

        if sigue_en_login(page):
            try:
                clave.press("Enter")
            except Exception:
                pass

        page.wait_for_timeout(1200)

        if login_exitoso(page):
            debug("Login correcto")
            return

    raise Exception("No se pudo iniciar sesión de verdad después de varios intentos.")


def abrir_ventas(page):
    debug("Abriendo menú VENTAS...")

    if not login_exitoso(page):
        raise Exception("Todavía no estoy dentro del sistema; el login no se completó.")

    elementos = page.locator("span, a, div, li")
    candidatos = []

    for i in range(elementos.count()):
        try:
            el = elementos.nth(i)
            if not el.is_visible(timeout=100):
                continue

            txt = el.inner_text(timeout=100).strip()
            if txt != "VENTAS":
                continue

            box = el.bounding_box()
            if box and box["x"] < 260 and box["y"] > 120:
                candidatos.append((el, box))
        except Exception:
            continue

    if not candidatos:
        raise Exception("No encontré el menú lateral VENTAS.")

    candidatos.sort(key=lambda x: (x[1]["x"], x[1]["y"]))
    ventas = candidatos[0][0]

    ventas.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    ventas.click(force=True)
    page.wait_for_timeout(1800)

    debug("VENTAS abierto")


def abrir_facturas(page):
    debug("Abriendo FACTURAS...")

    elementos = page.locator("span, a, div, li")
    candidatos = []

    for i in range(elementos.count()):
        try:
            el = elementos.nth(i)
            if not el.is_visible(timeout=100):
                continue

            txt = el.inner_text(timeout=100).strip().upper()
            if txt not in ["FACTURAS", "FACTURA"]:
                continue

            box = el.bounding_box()
            if box and box["x"] < 320 and box["y"] > 120:
                candidatos.append((el, box))
        except Exception:
            continue

    if not candidatos:
        raise Exception("No encontré FACTURAS.")

    candidatos.sort(key=lambda x: (x[1]["x"], x[1]["y"]))
    facturas = candidatos[0][0]

    facturas.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    facturas.click(force=True)
    page.wait_for_timeout(2200)

    debug("FACTURAS abierto")


def obtener_campo_factura(page):
    inputs = page.locator("input")
    campo = None

    for i in range(inputs.count()):
        try:
            inp = inputs.nth(i)
            if not inp.is_visible(timeout=100):
                continue

            box = inp.bounding_box()
            if box and 150 < box["x"] < 420 and 200 < box["y"] < 380:
                campo = inp
        except Exception:
            continue

    if not campo:
        raise Exception("No encontré el campo FACTURA.")

    return campo


def obtener_boton_filtro(page):
    botones = page.locator("button")
    boton = None

    for i in range(botones.count()):
        try:
            b = botones.nth(i)
            if not b.is_visible(timeout=100):
                continue

            box = b.bounding_box()
            if box and box["x"] > 800 and 180 < box["y"] < 360:
                boton = b
                break
        except Exception:
            continue

    if not boton:
        raise Exception("No encontré el botón filtro.")

    return boton


def filtrar_factura(page, nro_factura: str):
    debug(f"Escribiendo factura {nro_factura}...")

    campo = obtener_campo_factura(page)
    escribir_input(campo, nro_factura)
    page.wait_for_timeout(400)

    debug("Apretando filtro...")
    boton = obtener_boton_filtro(page)
    boton.click(force=True)
    page.wait_for_timeout(2200)

    debug("Filtro aplicado")


def obtener_fila_resultado(page, nro_factura: str):
    filas = page.locator("tr")

    for i in range(filas.count()):
        try:
            fila = filas.nth(i)
            if not fila.is_visible(timeout=100):
                continue

            texto = fila.inner_text(timeout=200)
            if nro_factura in texto:
                return fila
        except Exception:
            continue

    raise Exception(f"No encontré la fila del resultado para la factura {nro_factura}.")


def seleccionar_fila(page, nro_factura: str):
    debug("Seleccionando fila...")
    fila = obtener_fila_resultado(page, nro_factura)
    fila.click(force=True)
    page.wait_for_timeout(1200)
    debug("Fila seleccionada")


def apretar_imprimir(page):
    debug("Apretando IMPRIMIR...")
    boton = page.locator("button:has-text('IMPRIMIR')").first
    boton.wait_for(state="visible", timeout=10000)
    boton.click(force=True)
    page.wait_for_timeout(1800)
    debug("IMPRIMIR presionado")


def abrir_link_factura_ctrlf(context, page):
    debug("Intentando abrir el link final con estrategia Ctrl+F...")

    page.keyboard.press("Control+F")
    page.wait_for_timeout(600)
    page.keyboard.type("visualizar", delay=40)
    page.wait_for_timeout(1200)
    page.keyboard.press("Escape")
    page.wait_for_timeout(700)

    texto = page.locator("text=visualizar la factura").first
    texto.wait_for(state="visible", timeout=12000)

    texto.scroll_into_view_if_needed()
    page.wait_for_timeout(600)

    box = texto.bounding_box()
    if not box:
        raise Exception("No pude obtener la posición del texto final.")

    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2

    debug(f"Hover en x={x:.1f}, y={y:.1f}")
    page.mouse.move(x, y, steps=20)
    page.wait_for_timeout(800)

    try:
        with context.expect_page(timeout=8000) as nueva:
            page.mouse.click(x, y)

        factura = nueva.value
        factura.wait_for_load_state("domcontentloaded", timeout=30000)

        try:
            page.bring_to_front()
        except Exception:
            pass

        debug("Factura abierta en nueva pestaña.")
        return factura

    except Exception:
        debug("No abrió con click simple, probando doble click...")

    with context.expect_page(timeout=8000) as nueva:
        page.mouse.dblclick(x, y)

    factura = nueva.value
    factura.wait_for_load_state("domcontentloaded", timeout=30000)

    try:
        page.bring_to_front()
    except Exception:
        pass

    debug("Factura abierta con doble click.")
    return factura


def nombre_pdf_desde_url(url: str) -> str:
    nombre = url.split("/")[-1].split("?")[0].strip()
    if not nombre.lower().endswith(".pdf"):
        nombre += ".pdf"
    return nombre


def normalizar_nombre_cliente(nombre: str) -> str:
    nombre = nombre.strip().upper()

    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")

    nombre = re.sub(r"\s+", " ", nombre)

    caracteres_invalidos = r'[\\/:*?"<>|]'
    nombre = re.sub(caracteres_invalidos, "", nombre)

    nombre = nombre.replace(".", "")
    nombre = nombre.replace(",", "")
    nombre = nombre.replace("(", "")
    nombre = nombre.replace(")", "")
    nombre = nombre.replace("'", "")
    nombre = nombre.replace("’", "")

    nombre = re.sub(r"\s+", "_", nombre)
    nombre = re.sub(r"_+", "_", nombre)

    return nombre.strip("_")


def extraer_nombre_cliente_desde_pdf(ruta_pdf: Path) -> str | None:
    try:
        with pdfplumber.open(str(ruta_pdf)) as pdf:
            if not pdf.pages:
                return None

            texto = pdf.pages[0].extract_text() or ""
            if not texto.strip():
                return None

            patrones = [
                r"Nombre o razón\s+(.+?)\s+RUC[:\s]",
                r"Nombre o razon\s+(.+?)\s+RUC[:\s]",
            ]

            for patron in patrones:
                match = re.search(patron, texto, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    nombre = match.group(1).strip()
                    if nombre:
                        return normalizar_nombre_cliente(nombre)

    except Exception as e:
        debug(f"No pude leer nombre cliente desde PDF {ruta_pdf.name}: {e}")

    return None


def renombrar_pdf_con_cliente(ruta_pdf: Path, nro_factura: str) -> Path:
    nombre_cliente = extraer_nombre_cliente_desde_pdf(ruta_pdf)

    if not nombre_cliente:
        debug(f"No pude extraer cliente de factura {nro_factura}. Se deja nombre actual.")
        return ruta_pdf

    nuevo_nombre = f"{nombre_cliente}_{nro_factura}.pdf"
    nueva_ruta = ruta_pdf.with_name(nuevo_nombre)

    contador = 1
    while nueva_ruta.exists() and nueva_ruta != ruta_pdf:
        nueva_ruta = ruta_pdf.with_name(f"{nombre_cliente}_{nro_factura}_{contador}.pdf")
        contador += 1

    if nueva_ruta == ruta_pdf:
        return ruta_pdf

    ruta_pdf.rename(nueva_ruta)
    debug(f"PDF renombrado a: {nueva_ruta}")

    return nueva_ruta


def descargar_pdf_desde_pestana_pdf(factura_page, carpeta_destino: str, nro_factura: str) -> Path:
    debug("Preparando descarga del PDF...")

    pdf_url = factura_page.url
    if ".pdf" not in pdf_url.lower():
        raise Exception(f"La pestaña no parece ser un PDF directo. URL actual: {pdf_url}")

    destino = Path(carpeta_destino)
    destino.mkdir(parents=True, exist_ok=True)

    nombre_original = nombre_pdf_desde_url(pdf_url)
    nombre_temporal = f"Factura_{nro_factura}_{nombre_original}"
    ruta_temporal = destino / nombre_temporal

    debug(f"URL PDF detectada: {pdf_url}")
    debug(f"Guardando temporalmente en: {ruta_temporal}")

    response = factura_page.context.request.get(pdf_url, timeout=30000)
    if not response.ok:
        raise Exception(f"No se pudo descargar el PDF. Status: {response.status}")

    ruta_temporal.write_bytes(response.body())
    debug("PDF descargado correctamente.")

    ruta_final = renombrar_pdf_con_cliente(ruta_temporal, nro_factura)
    return ruta_final


def limpiar_busqueda_para_siguiente(page):
    try:
        campo = obtener_campo_factura(page)
        escribir_input(campo, "")
        page.wait_for_timeout(200)
    except Exception:
        pass


def procesar_factura(context, page, nro_factura: str) -> Path:
    debug("")
    debug(f"========== Procesando factura {nro_factura} ==========")

    filtrar_factura(page, nro_factura)
    seleccionar_fila(page, nro_factura)
    apretar_imprimir(page)
    factura_page = abrir_link_factura_ctrlf(context, page)
    ruta_pdf = descargar_pdf_desde_pestana_pdf(factura_page, CARPETA_DESCARGAS, nro_factura)

    try:
        factura_page.close()
    except Exception:
        pass

    try:
        page.bring_to_front()
    except Exception:
        pass

    limpiar_busqueda_para_siguiente(page)

    debug(f"Factura {nro_factura} terminada.")
    return ruta_pdf


def main():
    with sync_playwright() as p:
        facturas = leer_facturas_txt(ARCHIVO_FACTURAS)

        browser = p.chromium.launch(
            headless=False,
            slow_mo=250,
            args=["--start-maximized"]
        )

        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        descargadas = []
        fallidas = []

        try:
            hacer_login(page)
            abrir_ventas(page)
            abrir_facturas(page)

            for nro_factura in facturas:
                try:
                    ruta_pdf = procesar_factura(context, page, nro_factura)
                    descargadas.append((nro_factura, str(ruta_pdf)))
                except Exception as e:
                    debug(f"ERROR en factura {nro_factura}: {e}")
                    fallidas.append((nro_factura, str(e)))

                    try:
                        page.bring_to_front()
                    except Exception:
                        pass

                    try:
                        limpiar_busqueda_para_siguiente(page)
                    except Exception:
                        pass

            debug("")
            debug("========== RESUMEN ==========")
            debug(f"Descargadas: {len(descargadas)}")
            for nro, ruta in descargadas:
                debug(f"OK  {nro} -> {ruta}")

            debug(f"Fallidas: {len(fallidas)}")
            for nro, error in fallidas:
                debug(f"FAIL {nro} -> {error}")

            input("ENTER para cerrar")

        except Exception as e:
            debug(f"ERROR GENERAL: {e}")
            try:
                page.screenshot(path="error.png", full_page=True)
                debug("Screenshot guardado: error.png")
            except Exception:
                pass
            input("Error. ENTER para cerrar")

        browser.close()


if __name__ == "__main__":
    main()
