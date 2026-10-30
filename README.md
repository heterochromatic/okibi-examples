# okibi-examples

Example files used in the Okibi code-example guides.

## acme-orders

A small, fictional orders API: an OpenAPI 3.0.3 spec and an in-memory mock server that implements it. It is not a real product.

| File | What it is |
|---|---|
| [`acme-orders/openapi.json`](acme-orders/openapi.json) | The spec: 9 operations across orders, customers and products, `X-API-Key` auth, cursor pagination, typed errors |
| [`acme-orders/server.py`](acme-orders/server.py) | A mock of the API using only the Python standard library |

### Get the files

```bash
curl -fsSLO https://raw.githubusercontent.com/heterochromatic/okibi-examples/main/acme-orders/openapi.json
curl -fsSLO https://raw.githubusercontent.com/heterochromatic/okibi-examples/main/acme-orders/server.py
```

### Run the mock API

```bash
ACME_API_KEY=demo-key python3 server.py --port 8099
```

It listens on `http://127.0.0.1:8099/v1` and expects the key in the `X-API-Key` header. Data resets when you restart it (7 orders, 2 customers, 3 products).

### Operations

| Operation | Method and path |
|---|---|
| List orders (`status`, `customer_id`, `limit`, `cursor`) | `GET /orders` |
| Create an order | `POST /orders` |
| Get or update an order | `GET`, `PATCH /orders/{id}` |
| Cancel an order (shipped orders return 409) | `POST /orders/{id}/cancel` |
| List or create customers, get one | `GET`, `POST /customers`, `GET /customers/{id}` |
| List products | `GET /products` |
