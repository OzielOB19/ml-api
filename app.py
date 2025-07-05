from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import random
import os

app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
]

def scrape_product(search_term):
    url = f"https://listado.mercadolibre.com.mx/{search_term.replace(' ', '-')}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="es-MX",
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()

            # Navegación principal
            page.goto(url, timeout=60000)
            page.wait_for_selector(".ui-search-layout__item", timeout=15000)

            # Extracción de datos del listado
            product = page.evaluate('''() => {
                const card = document.querySelector(".ui-search-layout__item");
                if (!card) return null;

                return {
                    title: card.querySelector(".ui-search-item__title")?.innerText.trim() || "Sin título",
                    price: card.querySelector(".andes-money-amount__fraction")?.innerText.trim() || "Sin precio",
                    link: card.querySelector("a.ui-search-link")?.href || ""
                };
            }''')

            if not product or not product["link"]:
                return {"error": "Producto no encontrado"}

            # Extracción de detalles del vendedor
            detail_page = context.new_page()
            detail_page.goto(product["link"], timeout=60000)
            detail_page.wait_for_selector(".ui-pdp-seller__label-text-with-icon", timeout=10000)
            
            seller = detail_page.evaluate('''() => {
                return document.querySelector(".ui-pdp-seller__label-text-with-icon")?.innerText.trim() || "Desconocido";
            }''')

            browser.close()

            return {
                "producto": product["title"],
                "precio": f"${product['price']} MXN",
                "url": product["link"],
                "vendedor": seller,
                "status": "success"
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

@app.route('/buscar', methods=['GET'])
def buscar():
    q = request.args.get('q')
    if not q:
        return jsonify({"error": "Falta el parámetro ?q", "status": "error"}), 400
    
    data = scrape_product(q)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))