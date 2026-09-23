# 🛍️ Instant E-Commerce WhatsApp API

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)

An instant, multi-tenant e-commerce backend built with **Python**, **FastAPI**, and **PostgreSQL**. Designed specifically for micro-merchants, local bakeries, home businesses, and pop-up shops, this platform bridges web storefronts directly to WhatsApp orders (`wa.me`) without requiring complex credit card gateways, heavy merchant fees, or native mobile apps.

🌐 **Live Interactive API Docs:** [https://instant-ecommerce-api.onrender.com/docs](https://instant-ecommerce-api.onrender.com/docs)  
🛍️ **Live Web Storefront:** [https://ahamednawafak.github.io/instant-ecommerce-api/](https://ahamednawafak.github.io/instant-ecommerce-api/)  
📁 **GitHub Repository:** [https://github.com/ahamednawafak/instant-ecommerce-api](https://github.com/ahamednawafak/instant-ecommerce-api)

---

## 📋 Comprehensive Platform Report

### 1. Overview & Problem Statement
In emerging markets and local commercial sectors, setting up full payment processing gateways (Stripe, PayPal, local bank acquiring networks) presents high onboarding friction: merchant registration delays, monthly compliance costs, and high transaction processing fees. 

However, **WhatsApp** is ubiquitous for customer communication in these regions. 

The **Instant E-Commerce WhatsApp API** decouples order management from payment processing. Merchants get a high-performance RESTful API backend that hosts multi-tenant product catalogs, calculates cart totals, formats order metadata, and outputs a single-tap WhatsApp link (`wa.me`) containing a pre-formatted order receipt.

---

### 2. High-Impact Target Use Cases

| Business Type | Common Challenge | How This Platform Solves It |
| :--- | :--- | :--- |
| **Boutique Bakeries & Home Cooks** | Daily changing menus, custom order notes (e.g., cake writing). | Dynamic product categories, custom text notes field in cart checkout. |
| **Instagram & Social Sellers** | DM order overload ("Price in DM"), lost customer details. | Unified website catalog link in bio; outputs standardized receipt to WhatsApp. |
| **Pop-Up & Food Truck Outlets** | Fast customer queueing, need for quick mobile browsing. | Zero app-install web storefront (`index.html`) optimized for mobile web browsers. |
| **Local Grocery & Artisan Stores** | High commission rates on delivery aggregator platforms. | Direct merchant-to-customer ordering with zero transaction fees or commissions. |

---

### 3. Core Architectural & Business Features

- 🏪 **Multi-Tenant Architecture:** Host thousands of unique vendors on a single API deploy using isolated store slugs (`/stores/{slug}`).
- 🏷️ **Dynamic Product Categorization:** Organize product catalogs by categories (*Cakes, Pastries, Beverages, Desserts*) with instant category list endpoints (`GET /stores/{slug}/categories`).
- 🛒 **Multi-Item Cart Processing:** Calculate complex carts containing multiple distinct products and variable quantities in a single payload.
- 🐘 **Resilient Database Persistence:** Powered by **Render PostgreSQL** with automatic schema auto-migration execution on startup.
- 🌐 **Cross-Origin Resource Sharing (CORS):** Fully equipped with pre-configured `CORSMiddleware` to allow web apps, React frontends, and static HTML files to query data securely.
- ⚡ **URL-Encoded Checkout Engine:** Automatically validates item availability, applies currency symbols, formats order details, and outputs standard `wa.me` links.

---

## 🚀 How the WhatsApp Checkout Flow Works

```text
[ Web Fronted / index.html ] ──> [ Sends Multi-Item Cart Payload ]
                                              │
                                              │ POST /stores/{slug}/checkout/whatsapp
                                              ▼
                                   [ FastAPI Checkout Engine ]
                                              │
                                              │ 1. Queries PostgreSQL Database
                                              │ 2. Validates Stock & Item Prices
                                              │ 3. Formats Receipts & Delivery Details
                                              │ 4. URL-Encodes Message String
                                              ▼
[ Generated Redirect URL ] <──────────────────┘
  ([https://wa.me/97455551234?text=NEW%20ORDER](https://wa.me/97455551234?text=NEW%20ORDER)...)