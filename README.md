\# 🛍️ Instant E-Commerce WhatsApp API



\[!\[FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge\&logo=fastapi)](https://fastapi.tiangolo.com/)

\[!\[Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)](https://www.python.org/)

\[!\[SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge\&logo=sqlite\&logoColor=white)](https://www.sqlite.org/)

\[!\[Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge\&logo=render\&logoColor=black)](https://render.com/)



A lightweight multi-tenant e-commerce backend built with \*\*Python\*\* and \*\*FastAPI\*\*. Designed for local shops and home-based businesses, this API allows vendors to manage catalogs and generate structured \*\*instant WhatsApp order links\*\* without relying on complex payment gateways.



🌐 \*\*Live Interactive API Docs:\*\* https://instant-ecommerce-api.onrender.com/docs

\---



\## 🚀 How the WhatsApp Checkout Engine Works



```text

\[ Customer Browses API ] ──> \[ Sends Cart Payload ]

&#x20;                                          │

&#x20;                                          │ POST /stores/{slug}/checkout/whatsapp

&#x20;                                          ▼

&#x20;                               \[ FastAPI Order Engine ]

&#x20;                                          │

&#x20;                                          │ 1. Calculates Totals

&#x20;                                          │ 2. Formats Line Items \& Address

&#x20;                                          │ 3. Encodes Message URL

&#x20;                                          ▼

\[ Generated Redirect URL ] <───────────────┘

&#x20; (\[https://wa.me/97455551234?text=NEW%20ORDER](https://wa.me/97455551234?text=NEW%20ORDER)...)



✨ Core Features

🏪 Multi-Tenant Architecture: Host multiple independent vendors under unique store slugs (e.g., /stores/nawaf-bakery).



📦 Dynamic Product Catalogs: Store products with custom prices, stock status flags (in\_stock), and descriptions.



🔗 Instant WhatsApp Checkout Link: Automatically formats cart totals and generates safe percent-encoded WhatsApp URLs.



⚡ Auto-Generated Interactive Documentation: Live, interactive Swagger UI documentation at /docs.



☁️ Cloud Native \& Production Ready: Built with Python 3.14+, SQLAlchemy ORM, SQLite, and hosted on Render.

