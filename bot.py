import aiohttp, asyncio, base64, hashlib, json, math, random, re, signal, string, sys, time, traceback
from urllib.parse import urlparse
from pathlib import Path
import cv2, numpy as np
from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live
from rich import box

console = Console()

BASE_URL = "https://cryptifo.com/api"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
ORIGIN = "https://cryptifo.com"
REFERER = "https://cryptifo.com/"
TMO = 30
DLY = 1.0
REACT_MIN, REACT_MAX = 800, 2500
CAP_ATT, CAP_CONF = 15, 0.35
ACCT = Path("config.json")
OLD_ACCT = Path("account.json")
BCTT_HOST = "https://bitcotasks.com"
BCTT_UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
WARYONO_IN = "https://api.waryono.my.id/in.php"
WARYONO_RES = "https://api.waryono.my.id/res.php"

S, LK = {}, asyncio.Lock()
BCTT_LOG = Path("bctt.log")

def _b2i(b64):
    p = b64.split(",", 1)[-1] if "," in b64 else b64
    return cv2.imdecode(np.frombuffer(base64.b64decode(p), np.uint8), cv2.IMREAD_UNCHANGED)

def _edg(img):
    if img is None: return None
    if img.ndim == 3 and img.shape[2] == 4:
        a = img[:, :, 3:].astype(np.float32) / 255.0
        img = (img[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    return cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 50, 150)

def solve(bg, pk, mc=0.35):
    B, P = _edg(_b2i(bg)), _edg(_b2i(pk))
    if B is None or P is None: return None
    _, cf, _, loc = cv2.minMaxLoc(cv2.matchTemplate(B, P, cv2.TM_CCOEFF_NORMED))
    x = max(0, loc[0])
    return x if cf >= mc else None

def _fp():
    d = f"fp_{int(time.time() * 1000)}-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=11))
    return {"device_id": d, "timezone": -420}

def _ix():
    t1 = int(time.time() * 1000)
    t2 = t1 + random.randint(1000, 3000)
    m = t1 + (t2 - t1) // 2
    return {"mouse_events": [[random.randint(200, 600), random.randint(300, 500), t1],
                              [random.randint(200, 600), random.randint(300, 500), m],
                              [random.randint(200, 600), random.randint(300, 500), t2 - 500]],
            "start_ts": t1, "end_ts": t2}

def _traj(tx, ts):
    n = random.randint(15, 30)
    y = random.randint(280, 340)
    pt = [[0, y, ts]]
    for i in range(1, n + 1):
        t = i / n
        e = t * (2 - t)
        if t > 0.8 and random.random() > 0.7:
            e += random.uniform(1.0, 3.0) / tx
            ts += random.randint(10, 25)
        y = max(270, min(350, y + random.choice((-2, -1, 1, 2, -3, 3, 0))))
        ts += random.randint(8, 18)
        pt.append([int(tx * e), y, ts])
    pt.append([tx, y, ts])
    return pt

def _fmt(sec):
    s = max(0, int(sec))
    if s >= 3600: return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"
    if s >= 60: return f"{s // 60:02d}:{s % 60:02d}"
    return f"{s}s"

def _log_bctt(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        with open(BCTT_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def _load_cfg():
    cfg = {}
    if ACCT.exists():
        try: cfg = json.loads(ACCT.read_text()) or {}
        except: pass
    if (not cfg.get("email") or not cfg.get("password")) and OLD_ACCT.exists():
        try:
            old = json.loads(OLD_ACCT.read_text()) or {}
            cfg.setdefault("email", old.get("email", ""))
            cfg.setdefault("password", old.get("password", ""))
        except: pass
    return cfg

# ── Waryono external BitcoCaptcha solver ──────────────────────

class Waryono:
    def __init__(self, session, apikey):
        self._s, self._k = session, apikey

    async def _jp(self, url, **kw):
        kw.setdefault("timeout", aiohttp.ClientTimeout(total=TMO))
        kw.setdefault("headers", {})["Accept-Encoding"] = "gzip, deflate"  # FIX: hapus br
        try:
            async with self._s.post(url, **kw) as r:
                txt = await r.text()
                _log_bctt(f"WARYONO _jp status={r.status} body={txt[:200]}")
                try:
                    return json.loads(txt)
                except Exception:
                    return {}
        except Exception as ex:
            _log_bctt(f"WARYONO _jp exception: {ex}")
            return {}

    async def _jg(self, url, **kw):
        kw.setdefault("timeout", aiohttp.ClientTimeout(total=TMO))
        kw.setdefault("headers", {})["Accept-Encoding"] = "gzip, deflate"  # FIX: hapus br
        try:
            async with self._s.get(url, **kw) as r:
                txt = await r.text()
                try:
                    return json.loads(txt)
                except Exception:
                    return {}
        except Exception as ex:
            _log_bctt(f"WARYONO _jg exception: {ex}")
            return {}

    async def solve_bitco(self, body):
        _log_bctt(f"WARYONO submit body_keys={list(body.keys()) if isinstance(body, dict) else type(body)}")
        d = await self._jp(WARYONO_IN, json={
            "apikey": self._k,
            "methods": "bitcocaptcha",
            "type": "canvas",
            "body": body,
            "json": 1,
        })
        _log_bctt(f"WARYONO submit resp={d}")
        if d.get("status") != 1:
            return None
        tid = d.get("request")
        if not tid:
            return None
        for attempt in range(90):
            await asyncio.sleep(4)
            d = await self._jg(WARYONO_RES, params={
                "apikey": self._k, "id": tid, "action": "get", "json": 1,
            })
            req = str(d.get("request", ""))
            if d.get("status") == 1:
                _log_bctt(f"WARYONO solved={d.get('request')}")
                return d.get("request")
            if "NOT_READY" not in req.upper():
                _log_bctt(f"WARYONO failed={req}")
                return None
        _log_bctt("WARYONO timeout")
        return None

# ── BitcoTasks external PTC solver ────────────────────────────

_BCTT_CH_UA   = '"Chromium";v="125", "Not(A:Brand";v="24", "Google Chrome";v="125"'
_BCTT_CH_MOB  = "?1"
_BCTT_CH_PLAT = '"Android"'

class BcttSolver:
    def __init__(self, session, waryono):
        self._s = session
        self._w = waryono
        self._ua = BCTT_UA

    def _url(self, p):
        if not p:
            return BCTT_HOST
        if p.startswith("http"):
            return p
        base = BCTT_HOST.rstrip("/")
        path = p.lstrip("/")
        return f"{base}/{path}"

    def _fetch_site(self, url, referer):
        if not referer:
            return "none"
        try:
            h1 = urlparse(url).netloc
            h2 = urlparse(referer).netloc
            return "same-origin" if h1 == h2 else "cross-site"
        except Exception:
            return "none"

    def _hdr_get(self, url, referer=None):
        host = urlparse(url).netloc
        h = {
            "Host": host,
            "Sec-CH-UA": _BCTT_CH_UA,
            "Sec-CH-UA-Mobile": _BCTT_CH_MOB,
            "Sec-CH-UA-Platform": _BCTT_CH_PLAT,
            "User-Agent": self._ua,
            "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",  # FIX: hapus br
            "Sec-Fetch-Site": self._fetch_site(url, referer),
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "id-ID,id;q=0.9",
        }
        if referer:
            h["Referer"] = referer
        return h

    def _hdr_post(self, url, referer=None):
        host = urlparse(url).netloc
        h = {
            "Host": host,
            "Sec-CH-UA": _BCTT_CH_UA,
            "Sec-CH-UA-Mobile": _BCTT_CH_MOB,
            "Sec-CH-UA-Platform": _BCTT_CH_PLAT,
            "User-Agent": self._ua,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",  # FIX: hapus br
            "Content-Type": "application/x-www-form-urlencoded",
            "Sec-Fetch-Site": self._fetch_site(url, referer),
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "id-ID,id;q=0.9",
        }
        if referer:
            h["Referer"] = referer
        return h

    async def _gt(self, url, referer=None):
        actual = self._url(url)
        hdr = self._hdr_get(actual, referer)
        try:
            _log_bctt(f"GET {actual[:120]}")
            async with self._s.get(actual, headers=hdr, timeout=aiohttp.ClientTimeout(total=TMO)) as r:
                txt = await r.text()  # FIX: pakai text() bukan read()
                _log_bctt(f"GET => {len(txt)}ch status={r.status}")
                return txt
        except Exception as ex:
            _log_bctt(f"GET ERR {ex}")
            return ""

    async def _pj(self, url, data=None, referer=None):
        actual = self._url(url)
        hdr = self._hdr_post(actual, referer)
        try:
            _log_bctt(f"POST {actual[:120]} data_keys={list(data.keys()) if isinstance(data, dict) else '?'}")
            async with self._s.post(actual, headers=hdr, data=data, timeout=aiohttp.ClientTimeout(total=TMO)) as r:
                txt = await r.text()  # FIX: pakai text() bukan read()
                _log_bctt(f"POST => {r.status} body={txt[:300]}")
                try:
                    return json.loads(txt)
                except Exception:
                    _log_bctt(f"POST non-JSON: {txt[:200]}")
                    return {}
        except Exception as ex:
            _log_bctt(f"POST ERR {ex}")
            return {}

    async def run(self, url, tmr=5, on_status=None):
        if not url:
            _log_bctt("RUN: no url")
            return False
        start = time.time()
        try:
            _log_bctt(f"A: GET {url[:80]}")
            page0 = await self._gt(url)
            m = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", page0)
            if not m:
                _log_bctt(f"A: no redirect in {len(page0)}ch, body={page0[:300]}")
                return False
            dest = m.group(1)
            _log_bctt(f"A: dest={dest[:80]}")

            _log_bctt("B: GET dest first")
            page_pre = await self._gt(dest, referer=url)
            if "Forbidden" in page_pre:
                _log_bctt("B: Forbidden on initial GET!")
                return False

            _log_bctt("B: start_view")
            await self._pj(dest, data={"action": "start_view"}, referer=dest)

            page = await self._gt(dest, referer=dest)
            if "Forbidden" in page:
                _log_bctt("B: Forbidden!")
                return False

            p = self._params(page, tmr)
            if not p:
                _log_bctt(f"B: _params fail, page={len(page)}ch")
                for name in ["hash", "token", "sub_id", "api_key"]:
                    m = re.search(rf'name=["\']?{name}["\']?.{{0,80}}', page)
                    _log_bctt(f"  {name}: {'MATCH: '+m.group(0)[:80] if m else 'NOT FOUND'}")
                try:
                    with open("bctt_page.html", "w") as f:
                        f.write(page)
                    _log_bctt("  saved bctt_page.html")
                except Exception:
                    pass
                return False
            _log_bctt(f"B: timer={p['timer']} action={p['action']}")

            src = re.search(r'<script[^>]+src=["\']([^"\']*captcha2/[^"\']*)["\']', page)
            if not src:
                _log_bctt("C: no captcha2 script")
                return False
            _log_bctt(f"C: js={src.group(1)[:80]}")
            js = await self._gt(src.group(1), referer=dest)
            try:
                with open("bctt_cap.js", "w") as f:
                    f.write(js)
            except Exception:
                pass
            fjs = self._parse_js(js)
            if not fjs:
                _log_bctt(f"C: _parse_js fail, js={len(js)}ch")
                return False
            _log_bctt(f"C: Fid={fjs['cc_Fid']} Fnm={fjs['cc_Fnm']} ver={fjs['cc_ver']} end={fjs['cc_end']}")

            m2 = re.search(r'fetch\("([^"]+captcha[^"]+\.js\?action=captcha)"', js)
            ep = m2.group(1) if m2 else src.group(1)
            _log_bctt(f"D: ep={ep[:80]}")
            cap = await self._pj(ep, data={"t": int(time.time() * 1000), "r": random.random()},
                                  referer=dest)
            if not cap.get("options") or not cap.get("pixel"):
                _log_bctt(f"D: bad cap keys={list(cap.keys())}")
                return False
            _log_bctt(f"D: {len(cap['options'])} opts ch={str(cap.get('challenge',''))[:16]} diff={cap.get('difficulty')}")

            if on_status:
                await on_status("solving")
            sol = await self._solve(cap)
            if not sol:
                _log_bctt("E: solve failed")
                return False
            _log_bctt(f"E: ans={sol['cap']} nonce={sol['pow']['nonce']}")

            pl = self._payload(fjs, sol)
            _log_bctt(f"F: url={pl['url'][:60]} keys={list(pl['data'].keys())}")
            d = await self._pj(pl["url"], data=pl["data"], referer=dest)
            tok = d.get(fjs["cc_ver"])
            if not tok:
                _log_bctt(f"F: no tok, resp={json.dumps(d)[:200]}")
                return False
            _log_bctt(f"F: tok={str(tok)[:40]}")

            wait = p["timer"] - (time.time() - start)
            if on_status:
                await on_status("viewing", time.time() + max(0, wait), p["timer"])
            if wait > 0:
                _log_bctt(f"G: wait {math.ceil(wait)}s")
                await asyncio.sleep(math.ceil(wait))

            _log_bctt("H: final submit")
            ok = await self._submit(fjs, p, tok, dest)
            _log_bctt(f"H: {'OK' if ok else 'FAIL'}")
            return ok
        except Exception as ex:
            _log_bctt(f"RUN ERR: {ex}")
            return False

    def _params(self, page, tmr):
        tm = re.search(r'var\s+duration\s*=\s*(\d+)', page)
        p = {"hash": self._val(page, "hash"), "token": self._val(page, "token"),
             "sub_id": self._val(page, "sub_id"), "api_key": self._val(page, "api_key"),
             "timer": int(tm.group(1)) if tm else tmr, "action": self._action(page)}
        return p if None not in [p["hash"], p["token"], p["sub_id"], p["api_key"]] else None

    def _parse_js(self, js):
        r = {}
        m = re.search(r'var payload = "([^"]+)"', js)
        if m:
            skip = {"_et", "_mv", "_cf", "_pw", "_ch", "_bh"}
            r["cc_ran"] = {k: v for pair in m.group(1).split("&") if "=" in pair
                           for k, v in [pair.split("=", 1)] if k not in skip}
        m = re.search(r'<input type="hidden" id="([^"]+)" name="([^"]+)">', js)
        r["cc_Fid"] = m.group(1) if m else None
        r["cc_Fnm"] = m.group(2) if m else None
        m = re.search(r'xhr\.open\("POST",\s*"([^"]+captcha2[^"]+)"', js)
        r["cc_end"] = m.group(1) if m else None
        if r.get("cc_Fid"):
            m = re.search(r'getElementById\("' + re.escape(r["cc_Fid"]) + r'"\)\.value\s*=\s*response\.(\w+)', js)
            r["cc_ver"] = m.group(1) if m else None
        return r if all(r.get(k) for k in ("cc_ran", "cc_Fid", "cc_Fnm", "cc_end", "cc_ver")) else None

    async def _solve(self, data):
        ans = await self._w.solve_bitco(data)
        if ans is None:
            return None
        if isinstance(ans, str):
            m = re.search(r'array[:\s]*(\d+)', ans, re.IGNORECASE)
            if m:
                ans = int(m.group(1))
            else:
                try:
                    ans = int(ans)
                except (ValueError, TypeError):
                    pass
        ch, diff = data.get("challenge"), data.get("difficulty", 4)
        if ch is not None:
            pow_ = await asyncio.to_thread(self._pow, ch, diff)
        else:
            pow_ = {"nonce": 0, "hash": ""}
        return {"pow": {**pow_, "ch": ch}, "cap": ans}

    def _pow(self, challenge, difficulty):
        nonce, prefix = 0, "0" * difficulty
        while True:
            h = hashlib.sha256(f"{challenge}:{nonce}".encode()).hexdigest()
            if h.startswith(prefix):
                return {"nonce": nonce, "hash": h}
            nonce += 1

    def _payload(self, fjs, sol):
        keys = list(fjs["cc_ran"].keys())
        et, ch, n = random.randint(3000, 6000), sol["pow"]["ch"], sol["pow"]["nonce"]
        try:
            cap_val = json.dumps([int(sol["cap"])])
        except (ValueError, TypeError):
            cap_val = json.dumps([sol["cap"]])
        data = {
            keys[0]: fjs["cc_ran"][keys[0]], keys[1]: cap_val,
            "_et": et, "_mv": random.randint(2, 5), "_cf": 1894,
            "_pw": json.dumps({"nonce": n, "hash": sol["pow"].get("hash", "")}),
            "_ch": ch,
            "_bh": hashlib.sha256(f"{et}:{n}:{ch}".encode()).hexdigest(),
        }
        return {"url": fjs["cc_end"], "data": {k: v for k, v in data.items() if v not in ("", None)}}

    async def _submit(self, fjs, p, tok, referer):
        d = await self._pj("/system/ajax.php", data={
            "hash": p["hash"], "sub_id": p["sub_id"], "key": p["api_key"],
            "token": p["token"], fjs["cc_Fnm"]: tok, "action": p["action"],
        }, referer=referer)
        ok = d.get("status") == 200
        _log_bctt(f"SUBMIT status={d.get('status')} msg={d.get('message','')[:100]}")
        return ok

    def _val(self, html, name):
        m = re.search(rf'name=["\']?{re.escape(name)}["\']?\s+value=["\']([^"\']*)["\']', html)
        if not m:
            m = re.search(rf'value=["\']([^"\']*)["\'].*?name=["\']?{re.escape(name)}["\']?', html)
        if m:
            return m.group(1)
        m = re.search(rf"var\s+{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", html)
        return m.group(1) if m else None

    def _action(self, html):
        for pat in [r"action:\s*'([^']+)'", r"'action':\s*'([^']+)'", r'action\s*=\s*["\']([^"\']+)["\']']:
            m = re.search(pat, html)
            if m and m.group(1) != "start_view":
                return m.group(1)
        return "proccessLead"

class Client:
    def __init__(self, sess):
        self._s, self._tok, self._nc = sess, None, None

    def _h(self):
        h = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",  # FIX: hapus br
            "User-Agent": UA,
            "Origin": ORIGIN,
            "Referer": REFERER,
        }
        if self._tok: h["Authorization"] = f"Bearer {self._tok}"
        return h

    async def _r(self, m, p, **kw):
        try:
            kw.setdefault("timeout", aiohttp.ClientTimeout(total=TMO))
            kw["headers"] = self._h()
            if "json" in kw:
                kw["data"] = json.dumps(kw.pop("json"))
                kw["headers"]["Content-Type"] = "application/json"
            async with self._s.request(m, f"{BASE_URL}{p}", **kw) as r:
                # FIX: pakai text() lalu json.loads() agar tidak crash di Brotli
                if r.status != 204:
                    txt = await r.text()
                    try:
                        d = json.loads(txt)
                    except Exception:
                        d = {}
                else:
                    d = {}
                await asyncio.sleep(DLY + random.uniform(0, 0.5))
                return r.status, d
        except Exception:
            return 0, {}

    async def g(self, p):
        sc, d = await self._r("GET", p)
        return d if sc == 200 else None
    async def p(self, p, data):
        return await self._r("POST", p, json=data)

    async def login(self, em, pw, ct):
        sc, d = await self.p("/login", {"email": em, "password": pw, "captcha_token": ct})
        if sc in (200, 201) and d.get("token"):
            self._tok = d["token"]
            return True, d.get("user", {}).get("name", "?")
        return False, d.get("message", f"HTTP {sc}")

    async def sync(self):
        _, d = await self.p("/system/sync-status", {"bw": 1, "bh": 1, "nonce": self._nc})
        if d.get("next_nonce"): self._nc = d["next_nonce"]

    async def fs(self): return (await self.g("/faucet")) or {}
    async def cg(self): return (await self.g("/captcha/generate")) or {}

    async def cv(self, tok, xp, tr, rt):
        _, d = await self.p("/captcha/verify", {"token": tok, "x_pos": xp, "trajectory": tr, "reaction_time": rt})
        return (True, d) if d.get("success") and d.get("verified_token") else (False, d)

    async def fclaim(self, ct, fp, ix):
        sc, d = await self.p("/faucet/claim", {"captcha_token": ct, "fingerprint": fp, "interaction": ix})
        return (True, d) if sc in (200, 201) and (d.get("success") or d.get("reward")) else (False, d)

    async def ptc_list(self):
        d = await self.g("/ptc")
        return d if isinstance(d, list) else []

    async def ptc_verify(self, ad, ct, fp):
        sc, d = await self.p(f"/ptc/verify-start/{ad}", {"captcha_token": ct, "fingerprint": json.dumps(fp)})
        if sc in (200, 201) and d.get("view_token"): return d["view_token"]
        sc2, d2 = await self.p(f"/ptc/verify-start/{ad}", {"captcha_token": ct, "fingerprint": fp.get("device_id")})
        return d2.get("view_token") if sc2 in (200, 201) and d2.get("view_token") else None

    async def ptc_view(self, ad, vt):
        sc, d = await self.p(f"/ptc/start-view/{ad}", {"view_token": vt})
        return d if sc in (200, 201) else None
    async def ptc_surf(self, ad):
        sc, d = await self.p(f"/ptc/start-surf/{ad}", {})
        return d if sc in (200, 201) else None
    async def ptc_claim(self, ad, fp):
        sc, d = await self.p(f"/ptc/claim/{ad}", {"fingerprint": json.dumps(fp)})
        return (True, d) if sc in (200, 201) else (False, d)

class Bot:
    def __init__(self):
        self._coin, self._xp = 0.0, 0

    async def _sc(self, c):
        for _ in range(CAP_ATT):
            g = await c.cg()
            if not g.get("bg_image"):
                await asyncio.sleep(2); continue
            x = solve(g["bg_image"], g["piece_image"], CAP_CONF)
            if x is None:
                await asyncio.sleep(1.5); continue
            await asyncio.sleep(random.randint(REACT_MIN, REACT_MAX) / 1000)
            t0 = int(time.time() * 1000)
            ok, d = await c.cv(g["token"], x, _traj(x, t0), random.randint(REACT_MIN, REACT_MAX))
            if ok: return d["verified_token"]
            await asyncio.sleep(1.5)
        return None

    async def _faucet(self, c):
        while True:
            s = await c.fs()
            cd = int(s.get("time_left", 0))
            async with LK:
                S.update(f_deadline=time.time() + cd if cd > 0 else 0,
                         f_total=cd, f_status="cooldown" if cd > 0 else "ready")
                if cd > 0: S.pop("f_last", None)
            if cd > 0:
                await asyncio.sleep(cd + 3); continue
            await c.sync()
            async with LK: S["f_status"] = "captcha"
            ct = await self._sc(c)
            if ct is None:
                async with LK: S["f_status"] = "fail"; S.pop("f_last", None)
                await asyncio.sleep(30); continue
            async with LK: S["f_status"] = "claiming"
            ok, d = await c.fclaim(ct, _fp(), _ix())
            if ok:
                coin, xp = float(d.get("reward", 0) or 0), d.get("xp_earned", 0)
                async with LK:
                    self._coin += coin; self._xp += xp
                    S["f_last"] = f"+{coin} COIN  +{xp} XP"
                    S["f_status"] = "claimed"
            else:
                async with LK: S["f_status"] = "fail"; S.pop("f_last", None)
                await asyncio.sleep(30)

    async def _ptc(self, c):
        while True:
            ads = await c.ptc_list()
            local = [a for a in ads if a.get("type") != "api"]
            async with LK:
                S.update(p_status="idle", p_deadline=0)
            for ad in local:
                aid, dur = ad.get("id"), ad.get("duration_seconds", 30)
                async with LK:
                    S.update(p_duration=dur, p_deadline=0, p_status="verify")
                    S.pop("p_last", None)
                await c.sync()
                ct = await self._sc(c)
                if ct is None:
                    async with LK: S["p_status"] = "captcha fail"
                    continue
                vt = await c.ptc_verify(aid, ct, _fp())
                if not vt:
                    async with LK: S["p_status"] = "verify fail"
                    continue
                await c.sync()
                vd = await c.ptc_view(aid, vt) or await c.ptc_surf(aid)
                if not vd:
                    async with LK: S["p_status"] = "start fail"
                    continue
                dur = (vd.get("ad") or {}).get("duration_seconds", dur)
                async with LK:
                    S.update(p_duration=dur, p_deadline=time.time() + dur,
                             p_status="viewing")
                await asyncio.sleep(dur)
                await c.sync()
                ok, d = await c.ptc_claim(aid, _fp())
                if ok:
                    coin, xp = float(d.get("reward", 0) or 0), d.get("xp_earned", 0)
                    async with LK:
                        self._coin += coin; self._xp += xp
                        S["p_last"] = f"+{coin} COIN  +{xp} XP"
                        S.update(p_status="claimed", p_deadline=0)
                else:
                    async with LK: S.update(p_status="claim fail", p_deadline=0)
                await asyncio.sleep(random.uniform(2, 5))
            await asyncio.sleep(5)

    async def _ptc_api(self, c, sess, waryono):
        while True:
            ads = await c.ptc_list()
            ext = [a for a in ads if a.get("type") == "api"]
            async with LK:
                S.update(e_status="idle" if ext else "empty", e_deadline=0,
                         e_total=len(ext), e_duration=0, e_last="")
            for ad in ext:
                url, dur = ad.get("url"), int(ad.get("duration_seconds", 30) or 30)
                reward = float(ad.get("viewer_reward", 0) or 0)
                xp = int(ad.get("xp_reward", 0) or 0)
                title = (ad.get("title") or "External")[:24]
                async with LK:
                    S.update(e_status="solving", e_deadline=0, e_duration=dur, e_title=title)
                    S.pop("e_last", None)

                async def _on_st(st, dl=0, dr=0):
                    async with LK:
                        if st == "viewing":
                            S.update(e_status="viewing", e_deadline=dl, e_duration=dr or dur)
                        elif st == "solving":
                            S.update(e_status="solving", e_deadline=0)

                if "bitcotasks.com" in url:
                    bctt = BcttSolver(sess, waryono)
                    ok = await bctt.run(url, on_status=_on_st)
                    async with LK:
                        if ok:
                            self._coin += reward; self._xp += xp
                            S["e_last"] = f"+{reward} COIN  +{xp} XP"
                            S.update(e_status="claimed", e_deadline=0)
                        else:
                            S.update(e_status="fail", e_deadline=0)
                            S.pop("e_last", None)
                            await asyncio.sleep(5)
                    await asyncio.sleep(random.uniform(1, 3))
            await asyncio.sleep(random.uniform(1, 3))

    async def run(self):
        async with aiohttp.ClientSession() as sess:
            c = Client(sess)
            cfg = _load_cfg()
            e, pw, ak = cfg.get("email",""), cfg.get("password",""), cfg.get("apikey","")
            if not e or not pw:
                if not e: e = input("Email: ").strip()
                if not pw: pw = input("Password: ").strip()
            if not ak:
                ak = input("Waryono API Key: ").strip()
            ACCT.write_text(json.dumps({"email": e, "password": pw, "apikey": ak}, indent=2))
            ct = await self._sc(c)
            if ct is None: return console.log("[red]login captcha fail[/red]")
            ok, name = await c.login(e, pw, ct)
            if not ok: return console.log(f"[red]login: {name}[/red]")
            await c.sync()
            waryono = Waryono(sess, ak)
            t0 = time.time()
            async with LK:
                S.update(started=t0,
                         f_status="idle", f_deadline=0, f_total=0, f_last="",
                         p_status="idle", p_deadline=0, p_duration=0, p_last="",
                         e_status="idle", e_deadline=0, e_total=0, e_duration=0, e_last="", e_title="")

            async def _render(live):
                while True:
                    now = time.time()
                    async with LK:
                        fs = S.get("f_status", "idle")
                        ps = S.get("p_status", "idle")
                        fd = S.get("f_deadline", 0) or 0
                        ft = S.get("f_total", 0) or 1
                        pd = S.get("p_deadline", 0) or 0
                        pt_v = S.get("p_duration", 0) or 1
                        fl = max(0, fd - now)
                        pl = max(0, pd - now)
                        f_last = S.get("f_last", "")
                        p_last = S.get("p_last", "")
                        up = now - t0
                        coin = self._coin
                        xp = self._xp
                        es = S.get("e_status", "idle")
                        ed = S.get("e_deadline", 0) or 0
                        et_v = S.get("e_duration", 0) or 1
                        el = max(0, ed - now)
                        e_last = S.get("e_last", "")
                        e_title = S.get("e_title", "External")
                        e_total = S.get("e_total", 0)

                    pw = max(44, console.width - 4)

                    f_lines = []
                    if fs == "cooldown" and ft > 0:
                        f_lines.append(f"[yellow]cooldown  {_fmt(fl)} / {_fmt(ft)}[/yellow]")
                    elif fs == "captcha":
                        f_lines.append("[yellow]solving captcha[/yellow]")
                    elif fs == "claiming":
                        f_lines.append("[cyan]claiming[/cyan]")
                    elif fs == "claimed" and f_last:
                        f_lines.append(f"[green]{f_last}[/green]")
                    elif fs == "fail":
                        f_lines.append("[red]claim failed[/red]")
                    else:
                        f_lines.append("[dim]waiting[/dim]")
                    fp = Panel("\n".join(f_lines), title="Faucet", title_align="left",
                               border_style="cyan", box=box.ROUNDED, width=pw)

                    p_lines = []
                    if ps == "viewing" and pt_v > 0:
                        p_lines.append(f"[cyan]viewing  {_fmt(pl)} / {_fmt(pt_v)}[/cyan]")
                    elif ps == "verify":
                        p_lines.append("[yellow]verifying[/yellow]")
                    elif ps == "claimed" and p_last:
                        p_lines.append(f"[green]{p_last}[/green]")
                    elif ps in ("captcha fail", "verify fail", "start fail", "claim fail"):
                        p_lines.append(f"[red]{ps}[/red]")
                    else:
                        p_lines.append("[dim]waiting[/dim]")
                    pp = Panel("\n".join(p_lines), title="PTC", title_align="left",
                               border_style="cyan", box=box.ROUNDED, width=pw)

                    e_lines = []
                    if es == "viewing" and et_v > 0:
                        e_lines.append(f"[cyan]viewing  {_fmt(el)} / {_fmt(et_v)}[/cyan]")
                    elif es == "solving":
                        e_lines.append("[yellow]solving captcha[/yellow]")
                    elif es == "claimed" and e_last:
                        e_lines.append(f"[green]{e_last}[/green]")
                    elif es == "fail":
                        e_lines.append("[red]claim failed[/red]")
                    elif es == "empty":
                        e_lines.append("[dim]no external ads[/dim]")
                    else:
                        e_lines.append("[dim]waiting[/dim]")
                    epp = Panel("\n".join(e_lines), title=f"PTC External ({e_total})", title_align="left",
                                border_style="cyan", box=box.ROUNDED, width=pw)

                    s_lines = [f"[green]{coin:.4f} COIN[/green]  +{xp} XP  [dim]uptime {_fmt(up)}[/dim]"]
                    sp = Panel("\n".join(s_lines), title="Session", title_align="left",
                               border_style="dim", box=box.ROUNDED, width=pw)

                    live.update(Group(fp, pp, epp, sp))
                    await asyncio.sleep(0.5)

            live = Live((), console=console, refresh_per_second=2, screen=sys.stderr.isatty())
            live.start()
            try:
                await asyncio.gather(_render(live), self._faucet(c), self._ptc(c), self._ptc_api(c, sess, waryono))
            finally:
                live.stop()

def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    try:
        asyncio.run(Bot().run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.log(f"[red]fatal: {e}[/red]")
        traceback.print_exc()

if __name__ == "__main__":
    main()
