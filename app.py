from flask import Flask, request, jsonify
import asyncio
import random
from playwright.async_api import async_playwright

app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
]

async def scrape_product(search_term):
    url = f"https://listado.mercadolibre.com.mx/{search_term.replace(' ', '-')}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=random.choice(USER_AGENTS), locale="es-MX")
        page = await context.new_page()

        await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_selector(".ui-search-layout__item, .poly-card, .andes-card", timeout=15000)

        product = await page.evaluate('''() => {
            const card = document.querySelector(".ui-search-layout__item") ||
                         document.querySelector(".poly-card") ||
                         document.querySelector(".andes-card");
            if (!card) return null;

            const titleEl = card.querySelector(".ui-search-item__title") ||
                            card.querySelector(".poly-component__title") ||
                            card.querySelector(".andes-card__title");

            const priceEl = card.querySelector(".andes-money-amount__fraction") ||
                            card.querySelector(".price-tag-fraction");

            const linkEl = card.querySelector("a.ui-search-link") ||
                           card.querySelector("a.poly-component__title") ||
                           card.querySelector("a.andes-card__link");

            const title = titleEl?.innerText.trim() || "Sin título";
            const price = priceEl?.innerText.trim() || "Sin precio";
            const link = linkEl?.href || "";

            return { title, price, link };
        }''')

        if not product or not product["link"]:
            return {"error": "Producto no encontrado"}

        detail = await context.new_page()
        await detail.goto(product["link"], timeout=60000, wait_until="domcontentloaded")
        await detail.wait_for_timeout(3000)

        seller = await detail.evaluate('''() => {
            const el = document.querySelector(".ui-pdp-seller__label-text-with-icon");
            return el?.innerText.trim() || "Desconocido";
        }''')

        await browser.close()

        return {
            "producto": product["title"],
            "precio": f"${product['price']} MXN",
            "url": product["link"],
            "vendedor": seller
        }

@app.route('/buscar', methods=['GET'])
def buscar():
    q = request.args.get('q')
    if not q:
        return jsonify({"error": "Falta el parámetro ?q"}), 400
    data = asyncio.run(scrape_product(q))
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
