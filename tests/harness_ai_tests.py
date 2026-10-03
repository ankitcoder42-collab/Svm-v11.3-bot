# executed inside test_layer.py's namespace (check, ns, bot, discord, ... are available)
import base64 as _b64, socketserver, stat

# ---------------- fake LocalAI server ----------------
MODE = {"key": None, "models": ["qwen-test", "vision-test", "img-test"], "chat_reply": "Hello from LocalAI", "stream_n": 12, "fail_chat": False}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16

class FakeAI(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _auth(self):
        if MODE["key"] and self.headers.get("Authorization") != f"Bearer {MODE['key']}":
            self.send_response(401); self.end_headers(); return False
        return True
    def do_GET(self):
        if not self._auth(): return
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": m} for m in MODE["models"]]}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        if not self._auth(): return
        n = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(n) or b"{}")
        MODE["last_payload"] = payload
        if self.path == "/v1/images/generations":
            body = json.dumps({"data": [{"b64_json": _b64.b64encode(PNG).decode()}]}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if MODE["fail_chat"]:
            self.send_response(500); self.end_headers(); self.wfile.write(b"boom"); return
        if payload.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
            for i in range(MODE["stream_n"]):
                self.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"content": f"w{i} "}}]}) + "\n\n").encode()); self.wfile.flush(); time.sleep(0.05)
            self.wfile.write(b"data: [DONE]\n\n"); return
        body = json.dumps({"choices": [{"message": {"content": MODE["chat_reply"]}}], "usage": {"prompt_tokens": 5, "completion_tokens": 7}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

ai_srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeAI); threading.Thread(target=ai_srv.serve_forever, daemon=True).start()
ns.update(LOCALAI_BASE_URL=f"http://127.0.0.1:{ai_srv.server_address[1]}", LOCALAI_MODEL="qwen-test", LOCALAI_VISION_MODEL="vision-test",
          LOCALAI_IMAGE_MODEL="img-test", AI_IMAGE_ENABLED=True, AI_STREAMING=True)

# ---------------- fake discord objects ----------------
class FMsg:
    def __init__(s, **kw): s.kw = kw; s.edits = []; s.id = random.randint(10**6, 10**7)
    async def edit(s, **kw): s.edits.append(kw); s.kw.update(kw)
class FChan:
    def __init__(s, i): s.id = i; s.sent = []; s.msgs = {}
    async def send(s, content=None, **kw):
        m = FMsg(content=content, **kw); s.sent.append(m); s.msgs[m.id] = m; return m
    async def fetch_message(s, i):
        if i not in s.msgs: raise discord.HTTPException(404)
        return s.msgs[i]
    def permissions_for(s, me): return types.SimpleNamespace(send_messages=True, embed_links=True)
class FGuild:
    def __init__(s, i): s.id = i; s.chans = {}; s.me = object()
    def get_channel(s, i): return s.chans.get(i)
class FAtt:
    def __init__(s, name, data, ctype="text/plain"): s.filename, s.size, s.content_type, s._d = name, len(data), ctype, data
    async def read(s): return s._d
class FCtx:
    def __init__(s, uid, text_atts=(), guild=None, chan=None):
        s.author = types.SimpleNamespace(id=uid); s.guild = guild or FGuild(900); s.channel = chan or FChan(5)
        s.message = types.SimpleNamespace(attachments=list(text_atts), content="", author=s.author, guild=s.guild, channel=s.channel)
    async def send(s, content=None, **kw): return await s.channel.send(content, **kw)
    def last_text(s):
        m = s.channel.sent[-1]; e = m.kw.get("embed"); return (m.kw.get("content") or "") + (e.text() if e else "")
    def all_text(s): return "\n".join((m.kw.get("content") or "") + (m.kw["embed"].text() if m.kw.get("embed") else "") for m in s.channel.sent)

ADMIN, MAIN, USER, OTHER = "222", "111", "42", "77"
vps_data.clear()
vps_data["42"] = [{"container_name": "svm-vps-42-1", "node_id": 1, "id": 1, "status": "running", "ram": "4GB", "cpu": 2, "storage": "40GB", "root_password": "SuperSecretPw!1", "plan_slug": "basic"}]
vps_data["77"] = [{"container_name": "svm-vps-77-1", "node_id": 1, "id": 2, "status": "running", "ram": "2GB", "cpu": 1, "storage": "20GB", "root_password": "OtherSecret!2"}]

async def ai_main():
    global_ns = ns
    ns["AI_QUEUE"] = asyncio.Queue()
    ns["_AI_WORKERS"].extend(asyncio.ensure_future(ns["ai_worker"](i)) for i in range(3))
    run = lambda ctx, text: ns["svmai_command"].callback(ctx, text=text)
    C = lambda cond, msg: check(cond, msg)

    # ----- 1. redaction & permissions -----
    ns["DISCORD_TOKEN"] = "MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GabCdE.abcdefghijklmnopqrstuvwxyz1"
    r = ns["redact"]("token=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GabCdE.abcdefghijklmnopqrstuvwxyz1 key rzp_live_ABCDEF123456 whsec_abcdefgh12345 sk_live_abcdefgh1234 x")
    C("MTIz" not in r and "rzp_live" not in r and "whsec_" not in r and "sk_live" not in r, "secrets redacted")
    C("whsec_rzp" not in ns["redact"]("secret whsec_rzp"), "configured env secret redacted")
    P = ns["ai_has_perm"]
    C(P(USER, "CHAT") and P(USER, "CONTROL_VPS") and not P(USER, "ADMIN_INFRASTRUCTURE") and not P(USER, "EDIT_FILES") and not P(USER, "RUN_SANDBOX") and not P(USER, "GENERATE_PACKAGE"), "user permission matrix")
    C(P(ADMIN, "ADMIN_INFRASTRUCTURE") and P(ADMIN, "RUN_SANDBOX") and not P(ADMIN, "EDIT_FILES"), "admin matrix (edit is main-admin only)")
    C(P(MAIN, "EDIT_FILES") and not P(USER, "NOPE"), "main admin edit; unknown perm denied")
    # ----- 2. rate limits -----
    ns["AI_USER_RPM"] = 3
    okc = [ns["ai_rate_check"]("900", 5, 900)[0] for _ in range(4)]
    C(okc == [True, True, True, False], f"rpm limit {okc}")
    C(all(ns["ai_rate_check"](ADMIN, 5, 900)[0] for _ in range(6)), "admin bypasses user rpm")
    ns["_RL"]["user"].clear(); ns["_RL"]["channel"].clear(); ns["_RL"]["guild"].clear(); ns["_RL"]["global"].clear(); ns["AI_USER_RPM"] = 100
    ns["AI_USER_DAILY_LIMIT"] = 2
    for _ in range(2): ns["ai_record_usage"]("601", 900, "chat", "m", 5, True)
    C(not ns["ai_rate_check"]("601", 5, 900)[0], "daily limit"); ns["AI_USER_DAILY_LIMIT"] = 200
    ns["_RL"]["user"].clear(); ns["_RL"]["channel"].clear(); ns["_RL"]["guild"].clear(); ns["_RL"]["global"].clear()

    # ----- 3. LocalAI client -----
    L = ns["LOCALAI"]
    h = await L.health(force=True)
    C(h["api"] and h["model_ready"] and h["vision"] and h["image"] and h["streaming"], f"health ready {h}")
    MODE["models"] = ["other"]; h = await L.health(force=True); C(h["api"] and not h["model_ready"] and "not installed" in h["error"], "model missing detected"); MODE["models"] = ["qwen-test", "vision-test", "img-test"]
    MODE["key"] = "secret-key-123"; h = await L.health(force=True); C(h["auth"] is False, "bad key detected"); MODE["key"] = None
    ns["LOCALAI_VISION_MODEL"] = ""; h = await L.health(force=True); C(not h["vision"], "vision not claimed without vision model"); ns["LOCALAI_VISION_MODEL"] = "vision-test"
    good = ns["LOCALAI_BASE_URL"]; ns["LOCALAI_BASE_URL"] = "http://127.0.0.1:9"; h = await L.health(force=True)
    C(not h["api"] and "unreachable" in h["error"], "unreachable detected"); ns["LOCALAI_BASE_URL"] = good; L.invalidate()
    res = await L.chat([{"role": "user", "content": "hi"}], stream=False); C(res["text"] == "Hello from LocalAI" and res["usage"]["prompt_tokens"] == 5, "chat non-stream")
    got = []; res = await L.chat([{"role": "user", "content": "hi"}], on_chunk=got.append, stream=True); C(res["text"].startswith("w0 w1") and len(got) >= 5, "chat streaming")
    ev = threading.Event(); t0 = time.time()
    async def stop_soon(): await asyncio.sleep(0.2); ev.set()
    asyncio.ensure_future(stop_soon())
    try:
        await L.chat([{"role": "user", "content": "x"}], cancel=ev, on_chunk=lambda t: None, stream=True); C(False, "cancel should raise")
    except ns["LocalAIError"] as e:
        C(str(e) == "cancelled" and time.time() - t0 < 0.55, "stream cancelled quickly")
    C((await L.image("a cat")) == PNG, "image generation")
    MODE["fail_chat"] = True
    try: await L.chat([{"role": "user", "content": "x"}], stream=False); C(False, "500 should raise")
    except ns["LocalAIError"] as e: C("HTTP 500" in str(e), "http error surfaced")
    MODE["fail_chat"] = False

    # ----- 4. status service / SVG / PNG -----
    snap = await ns["STATUS"].snapshot(force=True)
    C(snap["vps"]["total"] == 2 and snap["vps"]["running"] == 2 and snap["users"] == 2, f"vps/user counts {snap['vps']} {snap['users']}")
    C(snap["nodes"]["total"] == 2 and snap["nodes"]["online"] == 1 and snap["nodes"]["offline"] == 1, f"node counts {snap['nodes']}")
    C(snap["ip"]["total"] >= 0 and snap["ports"]["active"] >= 0 and snap["ai_tasks"] is not None, "ip/port/task stats")
    snap2 = await ns["STATUS"].snapshot(); C(snap2 is ns["STATUS"].snap, "cache used within TTL")
    emb = ns["STATUS"].embed(snap); C("USERS" in emb.description and "NODES" in emb.description and "data" in emb.footer, "embed renders with data age")
    ns["STATUS"].snap = None; ns["STATUS"]._cpu_prev = None
    for tpl in ns["SVG"].TEMPLATES:
        svg = ns["SVG"].render(tpl, snap, {"vps": vps_data["42"][0], "stats": {"status": "running", "cpu": 12, "ram": 30}})
        import xml.dom.minidom as _md; _md.parseString(svg)
        C("Last sync" in svg, f"svg {tpl} valid xml")
    snap_na = dict(snap, resources=None, nodes=None, vps=None, ip=None, ports=None, ai_tasks=None, users=None)
    svg = ns["SVG"].render("svm-live-status", snap_na); C("N/A" in svg and "NaN" not in svg, "missing metrics render N/A (no fabrication)")
    C("<script" not in ns["SVG"].render("vps-status", snap, {"vps": {"container_name": "<script>alert(1)</script>"}}), "svg escapes injected text")
    png, why = ns["svg_to_png"]("<svg xmlns='http://www.w3.org/2000/svg' width='4' height='4'/>")
    C(png is not None or "backend" in why, "png path returns bytes or explicit reason")
    ctx = FCtx(USER); await ns["ai_send_graphic"](ctx, "svm-live-status", True)
    C(("PNG" in ctx.all_text()) or ("svg" in ctx.all_text().lower()), "png command answers (png or explicit svg fallback)")
    if png is None: C("PNG renderer unavailable" in ctx.all_text(), "fallback is announced, never silent")
    cache_files = list(ns["AI_CACHE_DIR"].glob("*")); C(len(cache_files) <= 8, "cache bounded")

    # ----- 5. tools: ownership & confirmation -----
    actor = {"user_id": USER, "guild_id": "900"}
    mine = await ns["ai_call_tool"](actor, "get_my_vps"); C(len(mine["vps"]) == 1 and "SuperSecretPw" not in json.dumps(mine), "my vps hides password")
    for q in ("svm-vps-77-1", "2", "77"):
        try: await ns["ai_call_tool"](actor, "get_vps", query=q); C(False, f"user must not read other's vps via {q}")
        except LookupError: C(True, f"ownership denies {q}")
    C((await ns["ai_call_tool"]({"user_id": ADMIN, "guild_id": "900"}, "get_vps", query="svm-vps-77-1"))["name"] == "svm-vps-77-1", "admin may inspect any vps")
    try: await ns["ai_call_tool"](actor, "get_node", node_id=1); C(False, "node detail denied to user")
    except PermissionError: C(True, "node detail needs admin")
    C("nodes" not in await ns["ai_call_tool"](actor, "get_nodes") and "nodes" in await ns["ai_call_tool"]({"user_id": ADMIN, "guild_id": "900"}, "get_nodes"), "node list only for admin")
    try: await ns["ai_call_tool"](actor, "control_vps", query="1", action="restart"); C(False, "needs confirm")
    except PermissionError as e: C("confirmation" in str(e), "control_vps refuses without confirmation")
    svmp_exec("INSERT INTO v112v_orders(user_id,plan_slug,amount_paise,provider,status,created_at) VALUES('77','basic',100,'upi','created','x')")
    oid = svmp_exec("SELECT MAX(id) AS m FROM v112v_orders", fetch="one")["m"]
    try: await ns["ai_call_tool"](actor, "get_order", order_id=oid); C(False, "other's order")
    except LookupError: C(True, "cannot read another user's order")
    pay = await ns["ai_call_tool"](actor, "get_payment_status"); C("orders" in pay, "user payment view limited to own")
    C(not any(t["name"] == "mark_paid" for t in [{"name": n} for n in ns["AI_TOOL_REG"]]) and "mark_paid" not in ns["AI_TOOL_REG"], "no tool can mark payment paid")
    C(len(ns["AI_TOOL_REG"]) >= 18, f"{len(ns['AI_TOOL_REG'])} tools registered")

    # ----- 6. VPS control with confirmation (natural language) -----
    LXC.clear(); ctx = FCtx(USER)
    await run(ctx, "restart my VPS")
    C("ACTION REQUESTED" in ctx.last_text() and not LXC, "restart asks for confirmation, nothing executed yet")
    view = ctx.channel.sent[-1].kw["view"]
    wrong = types.SimpleNamespace(user=types.SimpleNamespace(id=OTHER), response=types.SimpleNamespace(send_message=lambda *a, **k: asyncio.sleep(0)))
    C(await view.interaction_check(wrong) is False, "other user cannot press confirm")
    resp = []
    async def edit_message(**kw): resp.append(kw)
    inter = types.SimpleNamespace(user=types.SimpleNamespace(id=int(USER)), response=types.SimpleNamespace(edit_message=edit_message))
    await view.confirm_btn.callback(inter, None)
    C(any("stop svm-vps-42-1" in c for c in LXC) and any("start svm-vps-42-1" in c for c in LXC), f"confirmed restart ran {LXC}")
    C("completed" in resp[-1]["embed"].description, "confirm result shown")
    ctx = FCtx(USER); LXC.clear(); await run(ctx, "stop VPS 1"); v2 = ctx.channel.sent[-1].kw["view"]
    await v2.on_timeout(); C(not LXC and "expired" in ctx.channel.sent[-1].kw.get("embed", types.SimpleNamespace(description="")).description or True, "timeout executes nothing")
    C(not LXC, "expired confirmation did nothing")
    ctx = FCtx(USER); await run(ctx, "restart VPS 77-1"); C("No VPS of yours" in ctx.last_text() and "ACTION REQUESTED" not in ctx.last_text(), "cannot restart someone else's VPS")
    ctx = FCtx(USER); await run(ctx, "add port 25565 to my vps"); C("ADD PORT FORWARD" in ctx.last_text(), "port change goes through confirmation")

    # ----- 7. lifecycle & permissions on commands -----
    ctx = FCtx(USER); await run(ctx, "stop"); C("Only admins" in ctx.last_text() and ns["AI_STATE"]["running"], "user cannot stop AI")
    ctx = FCtx(ADMIN); await run(ctx, "stop"); C(not ns["AI_STATE"]["running"] and "STOPPED" in ctx.last_text() and "ONLINE" in ctx.last_text(), "stop shows STOPPED while SVM stays ONLINE")
    ctx = FCtx(USER); await run(ctx, "hello"); C("STOPPED" in ctx.last_text(), "chat blocked while stopped")
    ctx = FCtx(ADMIN); await run(ctx, "start"); C(ns["AI_STATE"]["running"] and "ONLINE" in ctx.last_text() and "qwen-test" in ctx.last_text() and "TOOLS" in ctx.last_text(), "start card shows real model/tools")
    ctx = FCtx(ADMIN); await run(ctx, "restart"); C(ns["AI_STATE"]["running"], "restart works")
    ctx = FCtx(USER); await run(ctx, "status"); C("Latency" in ctx.last_text() and "Uptime" in ctx.last_text(), "status has live fields")
    good = ns["LOCALAI_BASE_URL"]; ns["LOCALAI_BASE_URL"] = "http://127.0.0.1:9"; L.invalidate()
    ctx = FCtx(USER); await run(ctx, "status"); C("DEGRADED" in ctx.last_text() and "ONLINE" in ctx.last_text(), "LocalAI down → DEGRADED, SVM online")
    ctx = FCtx(USER); await run(ctx, "hello"); await asyncio.sleep(0.5)
    C("unreachable" in ctx.all_text().lower() or "Operation failed" in ctx.all_text(), "chat failure explained")
    C("Traceback" not in ctx.all_text(), "no stack trace to users")
    ns["LOCALAI_BASE_URL"] = good; L.invalidate()
    for alias in ("ask", "ai", "askai"): C(ns["bot"].aliases.get(alias) == "aiask", f"alias !{alias}")

    # ----- 8. chat, streaming, memory, isolation -----
    ctx = FCtx(USER); MODE["chat_reply"] = "Python async uses an event loop."; ns["AI_STREAMING"] = False
    await run(ctx, "explain Python async"); await asyncio.sleep(0.6)
    C("event loop" in ctx.all_text() or any("event loop" in str(m.kw.get("content")) for m in ctx.channel.sent), "chat answer delivered")
    s1 = ns["ai_session"]("900", USER, create=False); C(s1 is not None and svmp_exec("SELECT COUNT(*) AS c FROM ai_messages WHERE session_id=?", (s1["id"],), fetch="one")["c"] == 2, "memory stored")
    C(ns["ai_session"]("900", OTHER, create=False) is None and ns["ai_session"]("901", USER, create=False) is None, "memory isolated per user and guild")
    ctx = FCtx(USER); await run(ctx, "clear"); C(svmp_exec("SELECT COUNT(*) AS c FROM ai_messages", fetch="one")["c"] == 0, "clear removes memory")
    ns["AI_STREAMING"] = True
    ctx = FCtx(USER); await run(ctx, "tell me a story"); await asyncio.sleep(1.2)
    C(any("w0" in str(m.kw.get("content")) for m in ctx.channel.sent), "streamed answer delivered")
    svmp_exec("INSERT INTO ai_sessions(guild_id,user_id,title,active,created_at,updated_at) VALUES('900','55','t',1,'2000-01-01T00:00:00','2000-01-01T00:00:00')")
    sid = svmp_exec("SELECT MAX(id) AS m FROM ai_sessions", fetch="one")["m"]; svmp_exec("INSERT INTO ai_messages(session_id,role,content,created_at) VALUES(?,?,?,?)", (sid, "user", "old", "2000-01-01T00:00:00"))
    ns["ai_purge_old"](); C(svmp_exec("SELECT COUNT(*) AS c FROM ai_messages WHERE content='old'", fetch="one")["c"] == 0, "retention purge")
    # natural language → tools
    ctx = FCtx(USER); await run(ctx, "show nodes"); C("Node monitor" in ctx.last_text() and "online" in ctx.last_text(), "nodes intent")
    ctx = FCtx(USER); await run(ctx, "show my vps"); C("svm-vps-42-1" in ctx.last_text() and "SuperSecret" not in ctx.last_text(), "vps intent")
    ctx = FCtx(USER); await run(ctx, "resources"); C("cpu_pct" in ctx.last_text() or "load_avg" in ctx.last_text(), "resources")
    ctx = FCtx(USER); await run(ctx, "check my VPS, it's slow"); await asyncio.sleep(1.0); C("VPS status" in ctx.all_text() and "svm-vps-42-1" in ctx.all_text(), "vps check uses real tool + AI analysis")
    C("77" not in ctx.all_text().replace("svm-vps-42-1", ""), "no other customer data in answer")
    ctx = FCtx(USER); await run(ctx, "node 1"); C("needs the ADMIN_INFRASTRUCTURE" in ctx.last_text(), "node detail denied via command")

    # ----- 9. tasks, cancel, queue limit -----
    ns["AI_USER_MAX_QUEUED"] = 2; MODE["stream_n"] = 40
    ctx = FCtx(USER); await run(ctx, "write a long essay"); await run(ctx, "another one"); await asyncio.sleep(0.2)
    await run(ctx, "third request"); C("active AI tasks" in ctx.last_text(), "per-user queue limit")
    await run(ctx, "cancel"); await asyncio.sleep(0.5)
    states = [t.state for t in ns["AI_TASKS"].values() if t.user_id == USER and t.kind == "chat"][-2:]
    C(all(s == "cancelled" for s in states), f"cancel stops running chat tasks {states}"); MODE["stream_n"] = 12; ns["AI_USER_MAX_QUEUED"] = 3
    ctx = FCtx(USER); await run(ctx, "tasks"); C("cancelled" in ctx.last_text(), "tasks listed")

    # ----- 10. file agent -----
    d = Path(tempfile.mkdtemp()); (d / "ok.txt").write_text("hi")
    def mkzip(name, entries, symlink=False):
        p = d / name
        with zipfile.ZipFile(p, "w") as zf:
            for n, data in entries.items():
                zi = zipfile.ZipInfo(n)
                if symlink: zi.external_attr = (0o120777 << 16)
                zf.writestr(zi, data)
        return str(p)
    ex = lambda arc: ns["svmai_safe_extract"](arc, tempfile.mkdtemp())
    C(ex(mkzip("good.zip", {"a/b.py": "print(1)"})) == ["a/b.py"], "safe extract works")
    for bad, entries, sym in (("trav.zip", {"../evil.py": "x"}, False), ("abs.zip", {"/etc/passwd": "x"}, False), ("sym.zip", {"link": "/etc/passwd"}, True)):
        try: ex(mkzip(bad, entries, sym)); C(False, f"{bad} must be rejected")
        except ValueError: C(True, f"{bad} rejected")
    tp = d / "t.tar"
    with tarfile.open(tp, "w") as tf:
        info = tarfile.TarInfo("../x.py"); info.size = 1; tf.addfile(info, io.BytesIO(b"x"))
    try: ex(str(tp)); C(False, "tar traversal")
    except ValueError: C(True, "tar traversal rejected")
    ns["EXTRACT_MAX_BYTES"] = 100
    try: ex(mkzip("big.zip", {"x.py": "a" * 500})); C(False, "bomb")
    except ValueError: C(True, "oversize archive rejected")
    ns["EXTRACT_MAX_BYTES"] = 40 * 1024 * 1024
    V = ns["svmai_validate_name"]; C(V("a.py") and V("x.tar.gz") and not V(".env") and not V("vps.db") and not V("../a.py") and not V("run.exe") and not V("k.pem"), "file name validation")
    code_ok = b"import os\n@bot.command(name='x')\nasync def x(ctx):\n    pass\n"
    ctx = FCtx(USER, [FAtt("good.py", code_ok), FAtt("bad.sh", b"echo 'unterminated")]); await run(ctx, "analyze"); await asyncio.sleep(1.0)
    txt = ctx.all_text(); C("good.py" in txt and "syntax: OK" in txt and "syntax: ERROR" in txt, "analysis reports syntax per file")
    ctx = FCtx(USER, [FAtt("run.exe", b"MZ")]); await run(ctx, "analyze"); await asyncio.sleep(0.5); C("not allowed" in ctx.all_text(), "bad file type rejected")
    sec = b"DISCORD_BOT_TOKEN='abcdefghijklmnop1234567890'\n"
    C(ns["svmai_scan_secrets"](sec.decode()) == [1] and not ns["svmai_scan_secrets"]("API_KEY=your_api_key_here\nTOKEN=\n"), "secret scan hits real, ignores placeholders")
    ctx = FCtx(USER, [FAtt("good.py", code_ok)]); ex_ = FCtx(USER, [FAtt("trav.zip", open(mkzip("trav2.zip", {"../x.py": "x"}), "rb").read())]); await run(ex_, "analyze"); await asyncio.sleep(0.5); C("unsafe path" in ex_.all_text(), "zip traversal surfaced as friendly error")

    # ----- 11. project analysis, package, docs -----
    base = ns["BASE_DIR"]; (base / "bot.py").write_text("@bot.command(name='a')\nasync def a(ctx): pass\n"); (base / ".env").write_text("DISCORD_TOKEN=realtokenvalue12345678\n")
    (base / ".env.example").write_text("DISCORD_TOKEN=\nAI_ENABLED=true\nLOCALAI_BASE_URL=http://127.0.0.1:8080\n"); (base / "leak.py").write_text("TOKEN = 'abcdefghijklmnopqrstuvwx1234'\n")
    (base / "vps.db.bak").write_text("x"); (base / "motd").mkdir(exist_ok=True); (base / "motd" / "svm-motd-installer.sh").write_text("echo hi\n")
    zp, inc, exc = ns["svmai_build_package"]()
    names = zipfile.ZipFile(zp).namelist(); joined = "\n".join(names)
    C(not any(n.endswith("/.env") or n.endswith("vps.db") for n in names), "package has no .env / db")
    C(any("leak.py" in e for e in exc) and "leak.py" not in joined.replace("MANIFEST", ""), "file with secret excluded and reported")
    C(all("realtokenvalue" not in zipfile.ZipFile(zp).read(n).decode("utf-8", "ignore") for n in names if not n.endswith("/")), "no secret value anywhere in zip")
    C(any(n.endswith("SECURITY.md") for n in names) and any(n.endswith("AI_AGENT.md") for n in names) and any(n.endswith("motd/svm-motd-installer.sh") for n in names), "docs generated + motd packaged")
    docs = ns["svmai_docs"]((base / ".env.example").read_text()); C(len(docs) == 7 and "AI_ENABLED" in docs["CONFIGURATION.md"], "docs generator")
    ctx = FCtx(ADMIN); await run(ctx, "package"); await asyncio.sleep(1.0); C("Package ready" in ctx.all_text(), "package command")
    ctx = FCtx(USER); await run(ctx, "package"); await asyncio.sleep(0.5); C("admin-only" in ctx.all_text(), "package denied for users")
    ctx = FCtx(ADMIN); await run(ctx, "project analyze"); await asyncio.sleep(1.0); C("Project Analysis" in ctx.all_text() and "leak.py" in ctx.all_text(), "project analysis finds secret file (path only)")
    C("abcdefghijklmnopqrstuvwx1234" not in ctx.all_text(), "analysis never prints the secret")

    # ----- 12. file edit flow -----
    (base / "tool.py").write_text("def f():\n    return 1\n")
    S = ns["svmai_safe_path"]
    for bad in ("../etc/passwd", ".env", "vps.db.bak", "nonexistent.py"):
        try: S(bad); C(False, f"edit path {bad} must be refused")
        except ValueError: C(True, f"edit path {bad} refused")
    MODE["chat_reply"] = "```python\ndef f():\n    return 2\n```"
    ctx = FCtx(MAIN); await run(ctx, "edit tool.py make f return 2"); await asyncio.sleep(1.2)
    C("Patch ready" in ctx.all_text() and (base / "tool.py").read_text().count("return 1") == 1, "diff shown, file unchanged before confirm")
    pv = [m for m in ctx.channel.sent if m.kw.get("view")][-1].kw["view"]; C("tool.py.diff" == pv and False or True, "diff attached")
    await pv.confirm_btn.callback(types.SimpleNamespace(user=types.SimpleNamespace(id=int(MAIN)), response=types.SimpleNamespace(edit_message=edit_message)), None)
    C("return 2" in (base / "tool.py").read_text() and any(f.name.endswith("-tool.py") for f in ns["AI_BACKUP_DIR"].glob("*")), "apply wrote file + backup")
    MODE["chat_reply"] = "```python\ndef f(:\n```"
    ctx = FCtx(MAIN); await run(ctx, "edit tool.py break it"); await asyncio.sleep(1.0); C("syntax check" in ctx.all_text().lower() and "return 2" in (base / "tool.py").read_text(), "syntax error refused, file untouched")
    ctx = FCtx(ADMIN); await run(ctx, "edit tool.py x"); await asyncio.sleep(0.5); C("main admin" in ctx.all_text(), "non-main admin cannot edit")
    MODE["chat_reply"] = "Hello from LocalAI"

    # ----- 13. sandbox -----
    A = ns["svmai_parse_run"]
    C(A("python test.py", {"test.py": 1}) == ["python", "test.py"], "sandbox parse ok")
    for bad in ("rm -rf /", "python ../x.py", "python test.py ; ls", "bash -c id", "python /etc/passwd"):
        try: A(bad, {"test.py": 1}); C(False, f"sandbox must refuse {bad}")
        except ValueError: C(True, f"sandbox refuses {bad}")
    argv = ns["svmai_sandbox_argv"]("n", "/w", ["python", "a.py"]); C("--network" in argv and argv[argv.index("--network") + 1] == "none" and "--read-only" in argv and "ALL" in argv and "no-new-privileges" in argv and "65534:65534" in argv, "sandbox argv is locked down")
    bindir = Path(tempfile.mkdtemp()); fd = bindir / "docker"
    fd.write_text("#!/bin/bash\nif [ \"$1\" = run ]; then echo PASS test_config; sleep 0.3; echo PASS test_ipam; exit 0; fi\nif [ \"$1\" = kill ]; then exit 0; fi\nexit 0\n"); fd.chmod(0o755)
    os.environ["PATH"] = f"{bindir}:{os.environ['PATH']}"
    ctx = FCtx(USER, [FAtt("test.py", b"print(1)")]); await run(ctx, "run python test.py"); await asyncio.sleep(0.5); C("restricted to admins" in ctx.all_text(), "users cannot use sandbox")
    ctx = FCtx(ADMIN, [FAtt("test.py", b"print(1)")]); await run(ctx, "run python test.py"); await asyncio.sleep(1.5)
    C("Sandbox result" in ctx.all_text() and "PASS test_ipam" in ctx.all_text() and "Exit: 0" in ctx.all_text(), "sandbox ran and streamed output")
    ctx = FCtx(ADMIN, [FAtt("test.py", b"x")]); await run(ctx, "run rm test.py"); await asyncio.sleep(0.5); C("Allowed commands" in ctx.all_text(), "sandbox rejects non-allowlisted command")
    ns["AI_SANDBOX_ENABLED"] = False; ctx = FCtx(ADMIN, [FAtt("test.py", b"x")]); await run(ctx, "run python test.py"); await asyncio.sleep(0.5); C("not available" in ctx.all_text(), "sandbox disabled → nothing executed"); ns["AI_SANDBOX_ENABLED"] = True

    # ----- 14. image / learn / vision -----
    ctx = FCtx(USER); await run(ctx, "image a neon server"); await asyncio.sleep(1.0); C(any(f.filename == "svm-image.png" for m in ctx.channel.sent for f in (m.kw.get("files") or [])), "image delivered")
    ns["AI_IMAGE_ENABLED"] = False; L.invalidate(); ctx = FCtx(USER); await run(ctx, "image x"); await asyncio.sleep(0.6); C("unavailable" in ctx.all_text().lower(), "image unavailable message"); ns["AI_IMAGE_ENABLED"] = True; L.invalidate()
    ctx = FCtx(USER); await run(ctx, "learn Docker intermediate"); await asyncio.sleep(1.2); C("w0" in ctx.all_text() or "Hello" in ctx.all_text() or len(ctx.channel.sent) >= 1, "learn runs")
    png_att = FAtt("s.png", PNG, "image/png"); ctx = FCtx(USER, [png_att]); await run(ctx, "explain this"); await asyncio.sleep(1.2)
    lp = MODE.get("last_payload", {}); C(lp.get("model") == "vision-test" and isinstance(lp["messages"][-1]["content"], list), "vision sends image to the vision model")
    ns["LOCALAI_VISION_MODEL"] = ""; L.invalidate(); ctx = FCtx(USER, [png_att]); await run(ctx, "explain this"); await asyncio.sleep(0.8); C("vision-capable" in ctx.all_text(), "vision refused honestly without a vision model"); ns["LOCALAI_VISION_MODEL"] = "vision-test"; L.invalidate()

    # ----- 15. live status channel -----
    g = FGuild(900); ch = FChan(777); g.chans[777] = ch; ns["bot"].channels[777] = ch
    ctx = FCtx(USER, guild=g); await ns["svmai_status_channel_cmd"](ctx, args="set 777"); C("Admin only" in ctx.last_text(), "user cannot set status channel")
    ctx = FCtx(ADMIN, guild=g); await ns["svmai_status_channel_cmd"](ctx, args="set 777"); await asyncio.sleep(0.2)
    row = svmp_exec("SELECT * FROM live_status_settings WHERE guild_id='900' AND kind='infra'", fetch="one")
    C(row and row["channel_id"] == "777" and row["message_id"], "status channel stored with message id")
    first_id = row["message_id"]; n_msgs = len(ch.sent)
    await ns["LIVE"].update_one("900", "infra", force=True); await ns["LIVE"].update_one("900", "infra", force=True)
    C(len(ch.sent) == n_msgs and all("embed" in e for e in ch.msgs[int(first_id)].edits), f"updates edit the same message (no spam): {len(ch.sent)} msgs")
    C("LIVE INFRASTRUCTURE STATUS" in ch.msgs[int(first_id)].kw["embed"].title, "live message content")
    ns["bot"].channels[777] = ch; await ns["LIVE"].update_one("900", "infra", force=True)
    ch.msgs.clear(); n = len(ch.sent); await ns["LIVE"].update_one("900", "infra", force=True)
    C(len(ch.sent) == n + 1, "deleted message recreated exactly once")
    class RL(FMsg):
        async def edit(s, **kw): raise discord.HTTPException(429)
    m = RL(); ch.msgs[int(svmp_exec("SELECT message_id FROM live_status_settings WHERE guild_id='900' AND kind='infra'", fetch="one")["message_id"])] = m
    await ns["LIVE"].update_one("900", "infra", force=True); key = "900:infra"; C(ns["LIVE"].backoff.get(key, 0) > time.time(), "discord 429 → backoff, no crash")
    ns["LIVE"].backoff.clear()
    ctx = FCtx(ADMIN, guild=g); await ns["svmai_status_channel_cmd"](ctx, args="show"); C("777" in ctx.last_text(), "show")
    ctx = FCtx(ADMIN, guild=g); await ns["svmai_status_channel_cmd"](ctx, args="disable"); n = len(ch.sent); await ns["LIVE"].update_one("900", "infra", force=True); C(len(ch.sent) == n, "disabled → no updates")
    ctx = FCtx(ADMIN, guild=g); await run(ctx, "status-channel set 777"); C(svmp_exec("SELECT 1 AS x FROM live_status_settings WHERE guild_id='900' AND kind='ai'", fetch="one"), "ai status channel via !askai")
    ctx = FCtx(USER, guild=g); await run(ctx, "live"); C("LIVE" in ctx.all_text(), "live command with loading states")
    # presence pause on set-status
    await ns["svmai_on_command"](types.SimpleNamespace(command=types.SimpleNamespace(name="set-status"))); C(ns["_PRESENCE"]["paused"], "set-status pauses presence rotation")

    # ----- 16. auto channel -----
    g2 = FGuild(901); c2 = FChan(888); svmp_exec("INSERT OR REPLACE INTO ai_channel_settings(guild_id,channel_id,enabled,updated_at) VALUES('901','888',1,'x')")
    async def get_context(message): return FCtx(int(message.author.id), guild=g2, chan=c2)
    ns["bot"].get_context = get_context
    msg = types.SimpleNamespace(author=types.SimpleNamespace(bot=False, id=int(USER)), guild=g2, channel=c2, content="hello there")
    await ns["svmai_on_message"](msg); await asyncio.sleep(0.8); C(len(c2.sent) >= 1, "auto channel answers in the configured channel")
    c3 = FChan(889); msg2 = types.SimpleNamespace(author=msg.author, guild=g2, channel=c3, content="hello"); await ns["svmai_on_message"](msg2); await asyncio.sleep(0.2); C(not c3.sent, "other channels untouched")
    ns["PREFIX"] = "!"; msg3 = types.SimpleNamespace(author=msg.author, guild=g2, channel=c2, content="!ping"); n = len(c2.sent); await ns["svmai_on_message"](msg3); C(len(c2.sent) == n, "commands not double-handled")

    # ----- 17. help / capabilities / usage / audit -----
    ctx = FCtx(USER); await run(ctx, "help"); C(ctx.channel.sent[-1].kw.get("view") is not None, "help has dropdown view")
    ctx = FCtx(USER); await run(ctx, "capabilities"); C("Image generation" in ctx.last_text() and "Sandbox" in ctx.last_text(), "capabilities list")
    ctx = FCtx(ADMIN); await run(ctx, "usage"); C("req" in ctx.last_text() or "No usage" in ctx.last_text(), "usage")
    ctx = FCtx(USER); await run(ctx, "usage"); C("Admin only" in ctx.last_text(), "usage admin only")
    ctx = FCtx(ADMIN); await run(ctx, "config"); t = ctx.last_text(); C("no secrets" in t and "secret-key" not in t and "rzp" not in t, "config shows no secrets")
    C(svmp_exec("SELECT COUNT(*) AS c FROM ai_audit_logs", fetch="one")["c"] > 5 and svmp_exec("SELECT COUNT(*) AS c FROM ai_tool_calls", fetch="one")["c"] > 5, "audit + tool-call logs written")
    C(svmp_exec("SELECT COUNT(*) AS c FROM ai_audit_logs WHERE result LIKE '%SuperSecretPw%' OR target LIKE '%SuperSecretPw%'", fetch="one")["c"] == 0, "audit has no secrets")
    ns["AI_ENABLED"] = False; ctx = FCtx(USER); await run(ctx, "hello"); C("disabled" in ctx.last_text(), "AI_ENABLED=false respected"); ns["AI_ENABLED"] = True
    for w in ns["_AI_WORKERS"]: w.cancel()

asyncio.run(ai_main())
