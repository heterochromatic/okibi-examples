#!/usr/bin/env python3
"""Acme Orders: a small in-memory mock API used as the fixture for the Okibi guides.

Run:  ACME_API_KEY=demo-key python3 server.py --port 8099
Auth: send the key in the X-API-Key header.
"""
import argparse, json, os, re, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

STATUSES = ["pending", "paid", "shipped", "cancelled"]
CUSTOMERS = {f"cus_{i}": {"id": f"cus_{i}", "name": n, "email": e}
             for i, (n, e) in enumerate([("Ada Example", "ada@example.com"), ("Grace Sample", "grace@example.com")], 1)}
PRODUCTS = {f"prd_{i}": {"id": f"prd_{i}", "name": n, "price_cents": p}
            for i, (n, p) in enumerate([("Widget", 1250), ("Gadget", 4900), ("Gizmo", 999)], 1)}
ORDERS = {}
for i in range(1, 8):
    oid = f"ord_{i}"
    ORDERS[oid] = {"id": oid, "customer_id": f"cus_{1 + i % 2}", "status": STATUSES[i % 4],
                   "items": [{"product_id": f"prd_{1 + i % 3}", "quantity": 1 + i % 3}], "total_cents": 1250 * (1 + i % 3)}

def err(h, code, msg, kind="invalid_request"):
    h.send(code, {"error": {"type": kind, "message": msg}})

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try: return json.loads(self.rfile.read(n) or "{}")
        except Exception: return None
    def route(self, method):
        try: return self._route(method)
        except Exception: return err(self, 500, "internal error", "server_error")

    def _route(self, method):
        if self.headers.get("X-API-Key") != os.environ.get("ACME_API_KEY", "demo-key"):
            return err(self, 401, "Missing or invalid X-API-Key header", "unauthorized")
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}; p = u.path.rstrip("/")
        if method == "GET" and p == "/v1/orders":
            if "status" in q and q["status"] not in STATUSES:
                return err(self, 400, f"status must be one of {STATUSES}")
            rows = [o for o in ORDERS.values() if all(o.get(k) == v for k, v in q.items() if k in ("status", "customer_id"))]
            try: limit = int(q.get("limit", 3)); assert 1 <= limit <= 100
            except Exception: return err(self, 400, "limit must be an integer from 1 to 100")
            start = int(q["cursor"]) if q.get("cursor", "").isdigit() else 0
            page = rows[start:start + limit]; nxt = str(start + limit) if start + limit < len(rows) else None
            return self.send(200, {"data": page, "next_cursor": nxt})
        if method == "POST" and p == "/v1/orders":
            b = self.body()
            if not b or b.get("customer_id") not in CUSTOMERS: return err(self, 422, "customer_id must reference an existing customer")
            if not isinstance(b.get("items"), list) or not b["items"]: return err(self, 422, "items must contain at least one item")
            for i in b["items"]:
                if not isinstance(i, dict) or i.get("product_id") not in PRODUCTS: return err(self, 422, "each item needs a product_id that exists")
                q = i.get("quantity", 1)
                if isinstance(q, bool) or not isinstance(q, int) or q < 1: return err(self, 422, "quantity must be an integer of at least 1")
            oid = f"ord_{len(ORDERS) + 1}"
            total = sum(PRODUCTS.get(i.get("product_id"), {"price_cents": 0})["price_cents"] * i.get("quantity", 1) for i in b["items"])
            ORDERS[oid] = {"id": oid, "customer_id": b["customer_id"], "status": "pending", "items": b["items"], "total_cents": total}
            return self.send(201, ORDERS[oid])
        m = re.fullmatch(r"/v1/orders/([^/]+)", p)
        if m:
            o = ORDERS.get(m[1])
            if not o: return err(self, 404, f"order {m[1]} not found", "not_found")
            if method == "GET": return self.send(200, o)
            if method == "PATCH":
                b = self.body() or {}
                if "status" in b and b["status"] not in STATUSES: return err(self, 400, f"status must be one of {STATUSES}")
                o.update({k: v for k, v in b.items() if k in ("status",)}); return self.send(200, o)
        m = re.fullmatch(r"/v1/orders/([^/]+)/cancel", p)
        if method == "POST" and m:
            o = ORDERS.get(m[1])
            if not o: return err(self, 404, f"order {m[1]} not found", "not_found")
            if o["status"] == "shipped": return err(self, 409, "shipped orders cannot be cancelled", "conflict")
            o["status"] = "cancelled"; return self.send(200, o)
        if p == "/v1/customers":
            if method == "GET": return self.send(200, {"data": list(CUSTOMERS.values()), "next_cursor": None})
            if method == "POST":
                b = self.body()
                if not b or not b.get("name") or "@" not in b.get("email", ""): return err(self, 422, "name and a valid email are required")
                cid = f"cus_{len(CUSTOMERS) + 1}"; CUSTOMERS[cid] = {"id": cid, "name": b["name"], "email": b["email"]}
                return self.send(201, CUSTOMERS[cid])
        m = re.fullmatch(r"/v1/customers/([^/]+)", p)
        if method == "GET" and m:
            c = CUSTOMERS.get(m[1]); return self.send(200, c) if c else err(self, 404, f"customer {m[1]} not found", "not_found")
        if method == "GET" and p == "/v1/products": return self.send(200, {"data": list(PRODUCTS.values()), "next_cursor": None})
        err(self, 404, "no such route", "not_found")
    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PATCH(self): self.route("PATCH")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8099); a = ap.parse_args()
    print(f"Acme Orders mock on http://127.0.0.1:{a.port}  (X-API-Key: {os.environ.get('ACME_API_KEY', 'demo-key')})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
