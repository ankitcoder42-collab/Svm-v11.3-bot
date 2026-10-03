import asyncio, base64, hashlib, hmac, http.client, io, json, logging, os, random, re, shutil, socket, sqlite3, sys, tempfile, threading, time, types
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import requests

# ---- fake discord ----------------------------------------------------------
discord = types.ModuleType("discord")
class _HTTPException(Exception):
    def __init__(self, status=500): self.status = status
discord.Forbidden = type("Forbidden", (_HTTPException,), {}); discord.HTTPException = _HTTPException
class _Embed:
    def __init__(self, title=None, description=None, color=None, **k):
        self.title, self.description, self.color, self.fields, self.footer, self.image, self.timestamp = title, description, color, [], None, None, None
    def add_field(self, name, value, inline=True): self.fields.append((name, value, inline)); return self
    def set_footer(self, text=None, **k): self.footer = text; return self
    def set_image(self, url=None): self.image = url; return self
    def text(self): return f"{self.title}\n{self.description}\n" + "\n".join(f"{n}: {v}" for n, v, _ in self.fields)
discord.Embed = _Embed
class _File:
    def __init__(self, fp, filename=None): self.fp, self.filename = fp, filename
discord.File = _File
discord.ButtonStyle = types.SimpleNamespace(danger=1, secondary=2, primary=3)
discord.SelectOption = lambda **k: types.SimpleNamespace(**k)
discord.ActivityType = types.SimpleNamespace(watching=3, playing=0, listening=2, streaming=1)
discord.Activity = lambda **k: types.SimpleNamespace(**k)
class _View:
    def __init__(self, timeout=None):
        self.timeout, self.items = timeout, []
        for name in dir(type(self)):
            fn = getattr(type(self), name, None)
            kw = getattr(fn, "__ui_btn__", None)
            if kw is not None:
                setattr(self, name, types.SimpleNamespace(label=kw.get("label"), callback=(lambda i, b=None, fn=fn: fn(self, i, b))))
    def stop(self): self.stopped = True
    def add_item(self, it): self.items.append(it)
def _button(**kw):
    def deco(fn): fn.__ui_btn__ = kw; return fn
    return deco
discord.ui = types.SimpleNamespace(View=_View, button=_button, Select=lambda **k: types.SimpleNamespace(callback=None, **k))
ext = types.ModuleType("discord.ext"); tasks_mod = types.ModuleType("discord.ext.tasks")
class _Loop:
    def __init__(self, fn): self.fn = fn; self._r = False
    def start(self): self._r = True
    def is_running(self): return self._r
tasks_mod.loop = lambda **kw: (lambda fn: _Loop(fn))
ext.tasks = tasks_mod
sys.modules.update({"discord": discord, "discord.ext": ext, "discord.ext.tasks": tasks_mod})
import ast, subprocess, tarfile, zipfile, uuid, difflib, tempfile as _tf
from collections import deque
from xml.sax.saxutils import escape as _x

tmp = Path(tempfile.mkdtemp())
DB_FILE = str(tmp / "vps.db"); BASE_DIR = tmp
DB_LOCK = threading.RLock()
def get_db():
    c = sqlite3.connect(DB_FILE, timeout=30, check_same_thread=False); c.row_factory = sqlite3.Row; return c
c = get_db()
c.executescript("""
CREATE TABLE vps(id INTEGER PRIMARY KEY AUTOINCREMENT, container_name TEXT, node_id INTEGER, user_id TEXT);
CREATE TABLE port_forwards(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL,vps_container TEXT NOT NULL,vps_port INTEGER NOT NULL,host_port INTEGER NOT NULL,created_at TEXT NOT NULL,last_modified TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE v112v_plans(slug TEXT PRIMARY KEY,name TEXT,cpu INT,ram INT,disk INT,price_paise INT,active INT DEFAULT 1,created_at TEXT);
CREATE TABLE v112v_orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL,plan_slug TEXT NOT NULL,amount_paise INTEGER NOT NULL,currency TEXT DEFAULT 'INR',provider TEXT DEFAULT 'razorpay',provider_order_id TEXT UNIQUE,provider_payment_id TEXT UNIQUE,status TEXT DEFAULT 'created',screenshot_status TEXT DEFAULT 'none',created_at TEXT NOT NULL,verified_at TEXT,raw_event TEXT DEFAULT '');
CREATE TABLE v112v_provision_locks(order_id INTEGER PRIMARY KEY, acquired_at TEXT NOT NULL);
CREATE TABLE v112v_vps_meta(vps_db_id INTEGER PRIMARY KEY, vmid INTEGER, ipv4 TEXT DEFAULT '', ipv6 TEXT DEFAULT '', updated_at TEXT);
CREATE TABLE v112v_payment_proofs(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INT,user_id TEXT,sha256 TEXT,filename TEXT,ocr_text TEXT,status TEXT,created_at TEXT);
INSERT INTO v112v_plans VALUES('basic','Basic',2,4,40,10000,1,'x');
""")
c.commit(); c.close()

logger = logging.getLogger("t"); logging.basicConfig(level=logging.WARNING)
MAIN_ADMIN_ID = 111; PREFIX = "!"; YOUR_SERVER_IP = "1.2.3.4"; SVM_PUBLIC_URL = "https://pay.example.com"
RAZORPAY_KEY_ID = "rzp_test"; RAZORPAY_KEY_SECRET = "sec"; RAZORPAY_WEBHOOK_SECRET = "whsec_rzp"
UPI_ENABLED = True; UPI_ID = "me@upi"; UPI_NAME = "Me"; UPI_QR_URL = ""
PAYMENT_WEBHOOK_HOST = "127.0.0.1"; PAYMENT_WEBHOOK_PORT = 0
os.environ.update({"STRIPE_SECRET_KEY": "sk_test", "STRIPE_WEBHOOK_SECRET": "whsec_stripe", "PAYMENT_GATEWAYS": "razorpay,stripe,upi",
                   "PORT_RANGE_START": "30000", "PORT_RANGE_END": "30040", "PORT_RESERVED": "30001,30002", "IPAM_BIND_MODE": "nat",
                   "IPAM_POOL_MAX_ADDRS": "64"})
admin_data = {"admins": ["222"]}
vps_data = {"42": [{"container_name": "svm-vps-42-1", "node_id": 1, "id": 1, "plan_slug": "basic", "expiration_date": (datetime.now() - timedelta(days=2)).isoformat(),
                    "suspended": True, "suspension_history": [{"reason": "Auto-suspended due to VPS expiration on x"}], "status": "stopped"}]}
def razorpay_headers(): return {"Authorization": "Basic x"}
def add_field(e, n, v, i=False): e.setdefault("f", []).append((n, v))
def create_info_embed(t, d=""): return {"t": t, "d": d}
create_success_embed = create_error_embed = create_warning_embed = create_info_embed
class Bot:
    cmds = {}; aliases = {}; listeners = {}; latency = 0.05; channels = {}
    def command(self, name=None, **kw):
        def d(fn):
            self.cmds[name or fn.__name__] = fn; fn.callback = fn
            for a in kw.get("aliases", []): self.aliases[a] = name
            return fn
        return d
    def get_channel(self, i): return self.channels.get(i)
    async def fetch_channel(self, i): raise discord.HTTPException(404)
    async def change_presence(self, **k): pass
    def remove_command(self, n): self.cmds.pop(n, None)
    def add_listener(self, fn, name): self.listeners[name] = fn
    async def fetch_user(self, i):
        class U:
            async def send(s, embed=None): SENT.append(embed)
        return U()
bot = Bot(); SENT = []
def is_admin(): return lambda f: f
def get_node(nid): return {"id": nid, "is_local": True}
def get_nodes(): return [{"id": 1, "name": "Node-01", "is_local": True, "total_vps": 10}, {"id": 2, "name": "Node-02", "is_local": False, "total_vps": 5}]
async def get_node_status(nid): return "🟢 Online (Local)" if nid == 1 else "🔴 Offline"
def get_current_vps_count(nid): return 1
async def apply_internal_permissions(n, node): pass
def find_node_id_for_container(n): return 1
LXC = []; FAIL_ON = {"udp": False}
async def execute_lxc(container, command, timeout=120, node_id=None):
    if FAIL_ON["udp"] and "udp_proxy" in command and " add " in command: raise Exception("boom")
    LXC.append(command); return ""
async def safe_start_container(n, node): LXC.append("start " + n)
def save_vps_data(): pass
save_vps_data_immediate = save_vps_data
def get_user_allocation(u): return 5
def get_user_used_ports(u): return 0
def get_user_forwards(u): return []
def v112v_audit(*a, **k): pass
def v112v_get_plan(slug): return svmp_exec("SELECT * FROM v112v_plans WHERE slug=?", (slug,), fetch="one")
def v112v_find_vps(q): return None
def v112v_backfill_vmids(): pass
PROV = []
async def v112v_auto_provision_order(order_id):        # stands in for the original
    PROV.append(order_id); vps_data.setdefault("42", []).append({"container_name": f"new-{order_id}", "node_id": 1})
async def get_container_stats(*a, **k): return {}
async def _noop(): pass

_here = os.path.dirname(os.path.abspath(__file__))
src = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(_here, "..", "bot.py")).read()
start = src.index("# SVM+ V11.3 ADVANCED LAYER") - 80
end = src.index("# Run the bot (must stay LAST")
ns = globals()
ns["__file__"] = "x"
exec(compile(src[start:end].split("\n", 1)[1], "layer", "exec"), ns)

ok = 0
def check(cond, msg):
    global ok
    if not cond: print("FAIL:", msg); sys.exit(1)
    ok += 1

# 1 migration idempotent
svmp_migrate(); svmp_migrate(); check(True, "migrate")
# 2 CIDR
n, a, t = svmp_expand_cidr("10.0.0.0/29"); check(len(a) == 6 and not t, "/29 hosts")
n, a, t = svmp_expand_cidr("192.0.2.5/32"); check(len(a) == 1, "/32")
try: svmp_expand_cidr("10.0.0.0/16"); check(False, "big pool should raise")
except ValueError: check(True, "big pool raises")
n, a, t = svmp_expand_cidr("2001:db8::/64"); check(t and len(a) == 64, "v6 truncated")
# 3 pools / alloc
pid, cnt, _ = svmp_pool_add("pub", "203.0.113.0/29", gateway="203.0.113.1", node_id=1); check(cnt == 5, f"pool count {cnt}")
got = []
for i in range(5):
    r = svmp_ip_alloc(f"c{i}", i, 1, 4, "pub"); check(r is not None, "alloc"); got.append(r["address"])
check(len(set(got)) == 5 and "203.0.113.1" not in got, "unique, gateway excluded")
check(svmp_ip_alloc("x", 9, 1, 4, "pub") is None, "exhausted")
svmp_ip_free(got[0]); check(svmp_ip_alloc("again", 1, 1, 4, "pub")["address"] == got[0], "reuse after release")
os.environ["IPAM_POOLS"]="seed1|198.51.100.0/29|198.51.100.1;bad;seed1|10.9.9.0/29"
check(svmp_seed_pools()==1 and svmp_seed_pools()==0, "seed pools once")
check(svmp_exec("SELECT COUNT(*) AS c FROM svm_ipam WHERE pool_id=(SELECT id FROM svm_ip_pools WHERE name='seed1')",fetch="one")["c"]==5,"seed pool size")
# 4 ports
used = set()
for _ in range(25):
    p = get_available_host_port(1); check(p is not None and 30000 <= p <= 30040 and p not in (30001, 30002) and p not in used, f"port {p}")
    used.add(p)
_SVMP_PORT_INFLIGHT.clear()
# 5 create / remove forwards
async def t5():
    svmp_exec("INSERT INTO vps(container_name,node_id,user_id) VALUES('c1',1,'42')")
    hp = await create_port_forward("42", "c1", 25565, 1)
    check(hp and sum(1 for c in LXC if f"_proxy_{hp}" in c) == 2, "both protos created")
    hp2 = await create_port_forward("42", "c1", 22, 1); check(hp2 and sum(1 for c in LXC if f"tcp_proxy_{hp2}" in c) == 1 and not any(f"udp_proxy_{hp2}" in c for c in LXC), "ssh is tcp only")
    FAIL_ON["udp"] = True; before = svmp_exec("SELECT COUNT(*) AS c FROM port_forwards", fetch="one")["c"]
    bad = await create_port_forward("42", "c1", 9999, 1); FAIL_ON["udp"] = False
    check(bad is None and svmp_exec("SELECT COUNT(*) AS c FROM port_forwards", fetch="one")["c"] == before, "rollback on partial failure")
    check(any("remove" in c and "tcp_proxy" in c for c in LXC), "tcp device rolled back")
    fid = svmp_exec("SELECT id FROM port_forwards WHERE host_port=?", (hp,), fetch="one")["id"]
    okr, uid = await remove_port_forward(fid); check(okr and uid == "42", "removed")
    check(await create_port_forward("42", "c1", 0, 1) is None and await create_port_forward("42", "c1", 80, 1, "icmp") is None, "validation")
    n_sync = await svmp_ports_sync("c1"); check(isinstance(n_sync, tuple), "sync runs")
asyncio.run(t5())
# 6 NAT rule construction
HOST = []
async def svmp_host(*args, timeout=20):
    HOST.append(args); return (1 if "-C" in args else 0), "", ""
async def t6():
    okn, _ = await svmp_nat_apply("203.0.113.2", "10.10.0.5")
    check(okn and any("DNAT" in h for h in HOST) and any("SNAT" in h and "-I" in h for h in HOST), "nat rules added")
    try: await svmp_nat_apply("1.1.1.1; rm -rf /", "10.0.0.1"); check(False, "injection")
    except Exception: check(True, "ip validated")
asyncio.run(t6())
# 7 signatures
body = b'{"x":1}'
check(svmp_verify_razorpay_signature(body, hmac.new(b"whsec_rzp", body, hashlib.sha256).hexdigest()), "rzp sig ok")
check(not svmp_verify_razorpay_signature(body, "00"), "rzp sig bad")
def stripe_hdr(raw, ts=None, secret=b"whsec_stripe"):
    ts = ts or int(time.time()); return f"t={ts},v1=" + hmac.new(secret, f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
check(svmp_verify_stripe_signature(body, stripe_hdr(body)), "stripe sig ok")
check(not svmp_verify_stripe_signature(body + b" ", stripe_hdr(body)), "stripe tampered")
check(not svmp_verify_stripe_signature(body, stripe_hdr(body, ts=int(time.time()) - 4000)), "stripe replay window")
# 8 order lifecycle, razorpay (mock API confirm)
class R:
    def __init__(s, j): s.j = j; s.status_code = 200
    def raise_for_status(s): pass
    def json(s): return s.j
PAYSTATE = {"status": "captured", "amount": 10000}
requests.get = lambda url, **k: R({"amount": PAYSTATE["amount"], "currency": "INR", "status": PAYSTATE["status"]})
loop = asyncio.new_event_loop(); threading.Thread(target=loop.run_forever, daemon=True).start()
SVMP_LOOP = loop; ns["SVMP_LOOP"] = loop
oid = svmp_create_order("42", "basic", 10000, "razorpay"); svmp_exec("UPDATE v112v_orders SET gateway_ref='plink_1', provider_order_id='plink_1', gw_amount=10000 WHERE id=?", (oid,))
ev = {"event": "payment_link.paid", "payload": {"payment_link": {"entity": {"id": "plink_1"}}, "payment": {"entity": {"id": "pay_AAA111", "amount": 10000}}}}
PAYSTATE["status"] = "authorized"; check(svmp_handle_razorpay(ev).startswith("rejected"), "authorized rejected by default")
PAYSTATE["amount"] = 5; check(svmp_handle_razorpay(ev).startswith("rejected"), "amount mismatch rejected")
PAYSTATE.update(status="captured", amount=10000)
check(svmp_handle_razorpay(ev) == "paid", "captured accepted"); time.sleep(0.5)
check(svmp_handle_razorpay(ev).startswith("order already"), "duplicate ignored")
check(svmp_handle_razorpay({"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_AAA111", "order_id": "plink_1", "amount": 10000}}}}).startswith("order already"), "second event type ignored")
time.sleep(0.5)
check(PROV == [oid], f"provisioned exactly once {PROV}")
check(svmp_get_order(oid)["status"] == "provisioned", "status provisioned")
check(svmp_exec("SELECT COUNT(*) AS c FROM svm_billing", fetch="one")["c"] == 1, "billing row")
# 9 stripe
oid2 = svmp_create_order("42", "basic", 10000, "stripe"); svmp_exec("UPDATE v112v_orders SET gateway_ref='cs_1', provider_order_id='cs_1', gw_amount=10000 WHERE id=?", (oid2,))
sev = {"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {"id": "cs_1", "payment_status": "paid", "amount_total": 999, "currency": "inr", "payment_intent": "pi_1"}}}
check(svmp_handle_stripe(sev) == "rejected: amount mismatch", "stripe amount mismatch")
sev["data"]["object"]["amount_total"] = 10000; sev["data"]["object"]["currency"] = "usd"
check(svmp_handle_stripe(sev) == "rejected: amount mismatch", "stripe currency mismatch")
sev["data"]["object"]["currency"] = "inr"; check(svmp_handle_stripe(sev) == "paid", "stripe paid"); time.sleep(0.5)
check(PROV == [oid, oid2], "stripe provisioned once")
# 10 UPI approval + renewal + failure alert
oid3 = svmp_create_order("42", "basic", 10000, "upi", "renew", "svm-vps-42-1")
check(svmp_mark_order_paid(oid3, "upi-manual-3-222", "", "upi-admin", ("created", "expired")), "upi paid"); time.sleep(0.5)
v = vps_data["42"][0]
check(datetime.fromisoformat(v["expiration_date"]) > datetime.now() + timedelta(days=28), "renewal extended from now")
check(v["suspended"] is False and "start svm-vps-42-1" in LXC, "auto-suspended VPS restarted")
check(svmp_get_order(oid3)["status"] == "renewed", "renewed")
check(not svmp_mark_order_paid(oid3, "again", "", "x", ("created",)), "cannot pay twice")
async def failing(order_id): pass
_svmp_orig_provision = failing; ns["_svmp_orig_provision"] = failing
oid4 = svmp_create_order("42", "basic", 10000, "upi"); svmp_mark_order_paid(oid4, "upi-manual-4", "", "x"); time.sleep(0.5)
check(svmp_get_order(oid4)["status"] == "paid" and any("not provisioned" in str(e) for e in SENT), "paid-but-failed alerts admin")
# 11 webhook HTTP server end to end
PAYMENT_WEBHOOK_PORT = 0; ns["PAYMENT_WEBHOOK_PORT"] = 0
svmp_start_webhook_server(); srv = _SVMP_WEBHOOK["server"]; port = srv.server_address[1]
def post(path, raw, headers):
    cn = http.client.HTTPConnection("127.0.0.1", port); cn.request("POST", path, raw, headers); r = cn.getresponse(); return r.status, r.read()
st, _ = post("/razorpay/webhook", b"{}", {"X-Razorpay-Signature": "bad"}); check(st == 401, "bad sig 401")
raw = json.dumps({"event": "ping"}).encode(); sig = hmac.new(b"whsec_rzp", raw, hashlib.sha256).hexdigest()
st, body_ = post("/razorpay/webhook", raw, {"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "e1"}); check(st == 200 and body_ == b"ignored", f"signed ok {st} {body_}")
st, body_ = post("/razorpay/webhook", raw, {"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "e1"}); check(st == 200 and body_ == b"duplicate", "dedupe")
sraw = json.dumps({"id": "evt_9", "type": "other"}).encode(); st, _ = post("/stripe/webhook", sraw, {"Stripe-Signature": stripe_hdr(sraw)}); check(st == 200, "stripe webhook ok")
st, _ = post("/stripe/webhook", sraw, {"Stripe-Signature": "t=1,v1=00"}); check(st == 401, "stripe bad sig")
cn = http.client.HTTPConnection("127.0.0.1", port); cn.request("GET", "/health"); check(cn.getresponse().status == 200, "health")
check(set(svmp_enabled_gateways()) == {"razorpay", "stripe", "upi"}, "gateways enabled")
for name in ("ports", "ipool", "buy", "renew", "approve-order", "gateways", "portadmin", "svm-health"):
    check(name in bot.cmds, f"command {name} registered")
exec(compile(open(os.path.join(_here,"harness_ai_tests.py")).read(),"ai_tests","exec"), ns)
ok = ns["ok"] if "ok" in ns else ok
print(f"ALL {ns['ok']} CHECKS PASSED")
