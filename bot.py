import requests, base64, hashlib, json, math, random, re, string, sys, time, os

# ============================================================
# PROXY SETUP & LOGGING
# ============================================================
PROXIES = (lambda: {k.lower(): os.environ.get(k) for k in ["HTTPS_PROXY","HTTP_PROXY"] if os.environ.get(k)} or None)()
from urllib.parse import urlparse, urljoin
import cv2, numpy as np

BASE = "https://cryptifo.com/api"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
BCTT_UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
BCTT_HOST = "https://bitcotasks.com"

class C:
    R="\033[31m";G="\033[32m";Y="\033[33m";B="\033[34m"
    M="\033[35m";CY="\033[36m";W="\033[37m";D="\033[90m";X="\033[0m"

def log(tag, msg, color=C.W):
    ts = time.strftime("%H:%M:%S")
    print(f"{C.D}[{ts}]{C.X} {color}[{tag}]{C.X} {msg}")

def log_raw(tag, label, data, color=C.CY):
    """Log raw response/data dengan format yang rapi"""
    ts = time.strftime("%H:%M:%S")
    print(f"\n{C.D}[{ts}]{C.X} {color}[{tag}]{C.X} {C.Y}━━ {label} ━━{C.X}")
    if isinstance(data, dict):
        print(f"{C.D}{json.dumps(data, indent=2, ensure_ascii=False)}{C.X}")
    elif isinstance(data, str):
        # Truncate jika terlalu panjang
        if len(data) > 2000:
            print(f"{C.D}{data[:1000]}...\n[...truncated {len(data)-2000} chars...]\n{data[-1000:]}{C.X}")
        else:
            print(f"{C.D}{data}{C.X}")
    elif isinstance(data, bytes):
        print(f"{C.D}[bytes: {len(data)}]{C.X}")
    else:
        print(f"{C.D}{str(data)}{C.X}")
    print(f"{C.Y}{'━' * 40}{C.X}\n")

def log_proxy_info():
    """Log informasi proxy yang sedang digunakan"""
    if PROXIES:
        log("proxy", f"ACTIVE -> HTTP={PROXIES.get('http','-')} | HTTPS={PROXIES.get('https','-')}", C.G)
        for proto, url in PROXIES.items():
            try:
                parsed = urlparse(url)
                log("proxy", f"  {proto.upper()}: host={parsed.hostname}:{parsed.port} user={'***' if parsed.username else 'none'}", C.CY)
            except Exception as e:
                log("proxy", f"  {proto.upper()}: parse error: {e}", C.R)
    else:
        log("proxy", "NO PROXY CONFIGURED (direct connection)", C.Y)

def b2i(b64):
    p = b64.split(",", 1)[-1] if "," in b64 else b64
    return cv2.imdecode(np.frombuffer(base64.b64decode(p), np.uint8), cv2.IMREAD_UNCHANGED)

def edg(img):
    if img is None: return None
    if img.ndim == 3 and img.shape[2] == 4:
        a = img[:, :, 3:].astype(np.float32) / 255.0
        img = (img[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    return cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 50, 150)

def solve(bg, pk, mc=0.35):
    if (B := edg(b2i(bg))) is None or (P := edg(b2i(pk))) is None: return None
    _, cf, _, loc = cv2.minMaxLoc(cv2.matchTemplate(B, P, cv2.TM_CCOEFF_NORMED))
    return max(0, loc[0]) if cf >= mc else None

def fp():
    return {"device_id": f"fp_{int(time.time()*1000)}-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=11)),
            "timezone": -420}

def ix():
    t1 = int(time.time() * 1000); t2 = t1 + random.randint(1000, 3000)
    me = lambda t: [random.randint(200, 600), random.randint(300, 500), t]
    return {"mouse_events": [me(t1), me(t1 + (t2 - t1) // 2), me(t2 - 500)], "start_ts": t1, "end_ts": t2}

def traj(tx, ts):
    n = random.randint(15, 30); y = random.randint(280, 340); pt = [[0, y, ts]]
    for i in range(1, n + 1):
        t = i / n; e = t * (2 - t)
        if t > 0.8 and random.random() > 0.7:
            e += random.uniform(1.0, 3.0) / tx; ts += random.randint(10, 25)
        y = max(270, min(350, y + random.choice((-2,-1,1,2,-3,3,0)))); ts += random.randint(8, 18)
        pt.append([int(tx * e), y, ts])
    pt.append([tx, y, ts])
    return pt

def pow_(ch, diff):
    prefix = "0" * diff; nonce = 0
    while True:
        h = hashlib.sha256(f"{ch}:{nonce}".encode()).hexdigest()
        if h.startswith(prefix): return {"nonce": nonce, "hash": h}
        nonce += 1

def load_cfg(path="config.json"):
    try: cfg = json.load(open(path))
    except: cfg = {}
    cfg = {k: cfg.get(k) or input(f"{p}: ").strip()
           for k, p in [("email","Email"),("password","Password"),("apikey","Waryono API Key")]}
    json.dump(cfg, open(path, "w"), indent=2)
    return cfg.values()

class Waryono:
    def __init__(self, key): self._k = key

    def solve_bitco(self, body):
        try:
            log("waryono", "sending captcha to API...", C.B)
            payload = {"apikey": self._k, "methods": "bitcocaptcha", "type": "canvas", "body": body, "json": 1}
            log_raw("waryono", "REQUEST PAYLOAD", payload)

            d = requests.post("https://api.waryono.my.id/in.php",
                json=payload, timeout=30).json()
            log_raw("waryono", "IN.PHP RESPONSE", d, C.G)

            if d.get("status") != 1 or not (tid := d.get("request")):
                log("waryono", f"API error: status={d.get('status')} request={d.get('request')}", C.R)
                return None

            log("waryono", f"task_id={tid}, polling result...", C.Y)
            for attempt in range(90):
                time.sleep(4)
                r = requests.get("https://api.waryono.my.id/res.php",
                    params={"apikey": self._k, "id": tid, "action": "get", "json": 1}, timeout=30).json()
                log_raw("waryono", f"RES.PHP POLL #{attempt+1}", r, C.CY)
                if r.get("status") == 1:
                    log("waryono", f"solved: {r.get('request')}", C.G)
                    return r.get("request")
                if "NOT_READY" not in str(r.get("request", "")).upper():
                    log("waryono", f"unexpected response: {r.get('request')}", C.R)
                    return None
            log("waryono", "polling timeout (90 attempts)", C.R)
        except Exception as e:
            log("waryono", f"exception: {e}", C.R)
        return None

class BcttSolver:
    def __init__(self, w):
        self._w = w; self._s = requests.Session()
        if PROXIES: self._s.proxies.update(PROXIES)
        self._ua = BCTT_UA

    def _url(self, p):
        if not p: return BCTT_HOST
        if p.startswith("http"): return p
        return f"{BCTT_HOST.rstrip('/')}/{p.lstrip('/')}"

    def _fetch_site(self, url, ref):
        if not ref: return "none"
        try: return "same-origin" if urlparse(url).netloc == urlparse(ref).netloc else "cross-site"
        except: return "none"

    def _get(self, url, ref=None):
        actual = self._url(url)
        h = {
            "Host": urlparse(actual).netloc,
            "Sec-CH-UA": '"Chromium";v="125", "Not(A:Brand";v="24", "Google Chrome";v="125"',
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "User-Agent": self._ua,
            "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Sec-Fetch-Site": self._fetch_site(actual, ref),
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "id-ID,id;q=0.9",
        }
        if ref: h["Referer"] = ref
        try:
            log_raw("bctt-get", f"GET {actual[:80]}...", {"headers": h, "ref": ref}, C.B)
            r = self._s.get(actual, headers=h, timeout=30)
            log_raw("bctt-get", f"RESPONSE {r.status_code}", {"status": r.status_code, "content-length": len(r.text), "headers": dict(r.headers)}, C.G)
            return r.text
        except Exception as e:
            log("bctt-get", f"error: {e}", C.R)
            return ""

    def _post(self, url, data, ref=None):
        actual = self._url(url)
        h = {
            "Host": urlparse(actual).netloc,
            "Sec-CH-UA": '"Chromium";v="125", "Not(A:Brand";v="24", "Google Chrome";v="125"',
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "User-Agent": self._ua,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
            "Sec-Fetch-Site": self._fetch_site(actual, ref),
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "id-ID,id;q=0.9",
        }
        if ref: h["Referer"] = ref
        try:
            log_raw("bctt-post", f"POST {actual[:80]}...", {"headers": h, "data": data, "ref": ref}, C.B)
            r = self._s.post(actual, data=data, headers=h, timeout=30)
            log_raw("bctt-post", f"RESPONSE {r.status_code}", {"status": r.status_code, "content": r.text[:500], "headers": dict(r.headers)}, C.G)
            try:
                parsed = r.json()
                log_raw("bctt-post", "PARSED JSON", parsed, C.Y)
                return parsed
            except:
                log("bctt-post", "response is not JSON", C.Y)
                return {}
        except Exception as e:
            log("bctt-post", f"error: {e}", C.R)
            return {}

    def run(self, url, tmr=5):
        try:
            start = time.time()
            log("bctt", f"starting: {url[:60]}...", C.B)

            page0 = self._get(url)
            if not (m := re.search(r"window\.location\.href\s*=\s*['"]([^'"]+)['"]", page0)):
                log("bctt", "no redirect found in page0", C.R)
                return False
            dest = m.group(1)
            log("bctt", f"redirect -> {dest[:60]}...", C.CY)

            if "Forbidden" in self._get(dest, ref=url):
                log("bctt", "Forbidden on dest", C.R)
                return False

            start_resp = self._post(dest, {"action": "start_view"}, ref=dest)
            log_raw("bctt", "START_VIEW RESPONSE", start_resp, C.Y)

            page = self._get(dest, ref=dest)
            if "Forbidden" in page:
                log("bctt", "Forbidden on page", C.R)
                return False
            if not (p := self._params(page, tmr)):
                log("bctt", "params extraction failed", C.R)
                return False
            log_raw("bctt", "EXTRACTED PARAMS", p, C.M)

            if not (src := re.search(r'<script[^>]+src=["\']([^"\']*captcha2/[^"\']*)["\']', page)):
                log("bctt", "captcha script not found", C.R)
                return False
            log("bctt", f"captcha script: {src.group(1)[:60]}...", C.CY)

            js = self._get(src.group(1), ref=dest)
            if not (fjs := self._parse_js(js)):
                log("bctt", "JS parsing failed", C.R)
                return False
            log_raw("bctt", "PARSED JS VARS", fjs, C.M)

            m2 = re.search(r'fetch\("([^"]+captcha[^"]+\.js\?action=captcha)"', js)
            ep = m2.group(1) if m2 else src.group(1)

            cap = self._post(ep, {"t": int(time.time() * 1000), "r": random.random()}, ref=dest)
            if not cap.get("options") or not cap.get("pixel"):
                log("bctt", "captcha data incomplete", C.R)
                return False
            log_raw("bctt", "CAPTCHA DATA", {"options": cap.get("options", {})[:3] if isinstance(cap.get("options"), list) else cap.get("options"), 
                                             "pixel_len": len(cap.get("pixel","")), "challenge": cap.get("challenge")}, C.Y)

            if not (sol := self._solve(cap)):
                log("bctt", "captcha solving failed", C.R)
                return False
            log_raw("bctt", "CAPTCHA SOLUTION", sol, C.G)

            pl = self._payload(fjs, sol)
            log_raw("bctt", "PAYLOAD", pl, C.CY)

            d = self._post(pl["url"], pl["data"], ref=dest)
            if not (tok := d.get(fjs["cc_ver"])):
                log("bctt", f"token not found (expected key: {fjs['cc_ver']})", C.R)
                return False
            log("bctt", f"token received: {str(tok)[:30]}...", C.G)

            if (wait := p["timer"] - (time.time() - start)) > 0:
                log("bctt", f"waiting {math.ceil(wait)}s...", C.Y)
                time.sleep(math.ceil(wait))
            return self._submit(fjs, p, tok, dest)
        except Exception as e:
            log("bctt", f"error: {e}", C.R)
            import traceback
            log_raw("bctt", "TRACEBACK", traceback.format_exc(), C.R)
            return False

    def _val(self, html, name):
        for pat in [rf'name=["\']?{re.escape(name)}["\']?\s+value=["\']([^"\']*)["\']',
                    rf'value=["\']([^"\']*)["\'].*?name=["\']?{re.escape(name)}["\']?',
                    rf"var\s+{re.escape(name)}\s*=\s*['"]([^'"]+)['"]"]:
            if m := re.search(pat, html): return m.group(1)
        return None

    def _params(self, page, tmr):
        tm = re.search(r'var\s+duration\s*=\s*(\d+)', page)
        p = {"hash": self._val(page, "hash"), "token": self._val(page, "token"),
             "sub_id": self._val(page, "sub_id"), "api_key": self._val(page, "api_key"),
             "timer": int(tm.group(1)) if tm else tmr, "action": self._action(page)}
        return p if None not in p.values() else None

    def _action(self, html):
        for pat in [r"action:\s*'([^']+)'", r"'action':\s*'([^']+)'", r'action\s*=\s*["\']([^"\']+)["\']']:
            if (m := re.search(pat, html)) and m.group(1) != "start_view": return m.group(1)
        return "proccessLead"

    def _parse_js(self, js):
        r = {}; skip = {"_et", "_mv", "_cf", "_pw", "_ch", "_bh"}
        if m := re.search(r'(?:var|let|const)\s+payload\s*=\s*["\']([^"\']+)["\']', js) or re.search(r'var payload = "([^"]+)"', js):
            r["cc_ran"] = {k: v for pair in m.group(1).split("&") if "=" in pair
                           for k, v in [pair.split("=", 1)] if k not in skip}
        if m := re.search(r'<input\s+type=["\']hidden["\']\s+id=["\']([^"\']+)["\']\s+name=["\']([^"\']+)["\']>', js) or \
                re.search(r'<input\s+id=["\']([^"\']+)["\']\s+name=["\']([^"\']+)["\']\s+type=["\']hidden["\']>', js) or \
                re.search(r'<input type="hidden" id="([^"]+)" name="([^"]+)">', js):
            r["cc_Fid"], r["cc_Fnm"] = m.group(1), m.group(2)
        if m := re.search(r'xhr\.open\("POST",\s*["\']([^"\']+)["\']', js) or re.search(r'fetch\(\s*["\']([^"\']+)["\']', js):
            r["cc_end"] = m.group(1)
        if r.get("cc_Fid"):
            f_esc = re.escape(r["cc_Fid"])
            if m := re.search(r'getElementById\(["\']' + f_esc + r'["\']\)\.value\s*=\s*response\.(\w+)', js) or \
                    re.search(r'[\$\(]*["\']#' + f_esc + r'["\'][\)]*\.val\(response\.(\w+)\)', js):
                r["cc_ver"] = m.group(1)
        return r if all(r.get(k) for k in ("cc_ran", "cc_Fid", "cc_Fnm", "cc_end", "cc_ver")) else None

    def _solve(self, data):
        if (ans := self._w.solve_bitco(data)) is None: return None
        if isinstance(ans, str):
            ans = int(m.group(1)) if (m := re.search(r'array[:\s]*(\d+)', ans, re.I)) else int(ans)
        ch, diff = data.get("challenge"), data.get("difficulty", 4)
        pw = pow_(ch, diff) if ch is not None else {"nonce": 0, "hash": ""}
        return {"pow": {**pw, "ch": ch}, "cap": ans}

    def _payload(self, fjs, sol):
        keys = list(fjs["cc_ran"].keys()); et = random.randint(3000, 6000); n = sol["pow"]["nonce"]
        data = {
            keys[0]: fjs["cc_ran"][keys[0]], keys[1]: json.dumps([int(sol["cap"])]),
            "_et": et, "_mv": random.randint(2, 5), "_cf": 1894,
            "_pw": json.dumps({"nonce": n, "hash": sol["pow"].get("hash", "")}),
            "_ch": sol["pow"]["ch"],
            "_bh": hashlib.sha256(f"{et}:{n}:{sol['pow']['ch']}".encode()).hexdigest(),
        }
        return {"url": fjs["cc_end"], "data": {k: v for k, v in data.items() if v not in ("", None)}}

    def _submit(self, fjs, p, tok, ref):
        d = self._post("/system/ajax.php", {
            "hash": p["hash"], "sub_id": p["sub_id"], "key": p["api_key"],
            "token": p["token"], fjs["cc_Fnm"]: tok, "action": p["action"],
        }, ref=ref)
        ok = d.get("status") == 200
        log("bctt", f"submit {'OK' if ok else 'FAIL'} -> status={d.get('status')}", C.G if ok else C.R)
        log_raw("bctt", "FINAL SUBMIT RESPONSE", d, C.G if ok else C.R)
        return ok

# ============================================================
# CRYPTIFO CLIENT WITH FULL LOGGING
# ============================================================
class Client:
    def __init__(self):
        self._s = requests.Session()
        if PROXIES: self._s.proxies.update(PROXIES)
        self._s.headers.update({"Accept": "application/json", "User-Agent": UA,
                                "Origin": "https://cryptifo.com", "Referer": "https://cryptifo.com/",
                                "Accept-Encoding": "gzip, deflate"})
        self._tok = None

    def _req(self, m, p, data=None):
        h = {"Authorization": f"Bearer {self._tok}"} if self._tok else {}
        url = f"{BASE}{p}"
        try:
            log_raw("cryptifo", f"{m} {url}", {"headers": {**self._s.headers, **h}, "body": data}, C.B)
            r = self._s.request(m, url, json=data, headers=h, timeout=30)

            raw_info = {
                "status_code": r.status_code,
                "content_type": r.headers.get("Content-Type", "unknown"),
                "content_length": len(r.content),
                "response_headers": dict(r.headers),
            }
            log_raw("cryptifo", f"RESPONSE {r.status_code}", raw_info, C.G)

            try:
                parsed = r.json()
                log_raw("cryptifo", "PARSED JSON", parsed, C.Y)
                return r.status_code, parsed
            except json.JSONDecodeError:
                text_preview = r.text[:500] if r.text else "[empty]"
                log_raw("cryptifo", "RAW TEXT (not JSON)", text_preview, C.Y)
                return r.status_code, {}
        except Exception as e:
            log("net", str(e), C.R)
            log_raw("cryptifo", "REQUEST EXCEPTION", str(e), C.R)
            return 0, {}

    def g(self, p):
        s, d = self._req("GET", p)
        return d if s == 200 else None

    def p(self, p, data):
        return self._req("POST", p, data)

    def login(self, em, pw, ct):
        log("auth", f"attempting login for {em}", C.B)
        s, d = self.p("/login", {"email": em, "password": pw, "captcha_token": ct})
        log_raw("auth", f"LOGIN RESPONSE (HTTP {s})", d, C.G if s in (200,201) else C.R)
        if s in (200, 201) and d.get("token"):
            self._tok = d["token"]
            log("auth", f"logged in as {d.get('user', {}).get('name', '?')}", C.G)
            return True, d.get("user", {}).get("name", "?")
        return False, d.get("message", f"HTTP {s}")

    def sync(self):
        log("sync", "syncing...", C.D)
        return self.p("/system/sync-status", {"bw": 1, "bh": 1, "nonce": None})[1]

    def gen_captcha(self):
        log("captcha", "generating captcha...", C.B)
        result = self.g("/captcha/generate") or {}
        if result:
            log_raw("captcha", "GENERATE RESPONSE", {
                "token": result.get("token", "?"),
                "bg_image_len": len(result.get("bg_image", "")),
                "piece_image_len": len(result.get("piece_image", "")),
            }, C.Y)
        return result

    def verify_cap(self, tok, xp, tr, rt):
        log("captcha", f"verifying: token={tok[:20] if tok else '?'}... x_pos={xp}", C.B)
        _, d = self.p("/captcha/verify", {"token": tok, "x_pos": xp, "trajectory": tr, "reaction_time": rt})
        log_raw("captcha", "VERIFY RESPONSE", d, C.G if d.get("success") else C.R)
        return (True, d) if d.get("success") and d.get("verified_token") else (False, d)

    def claim_faucet(self, ct, f, i):
        log("faucet", "claiming...", C.B)
        s, d = self.p("/faucet/claim", {"captcha_token": ct, "fingerprint": f, "interaction": i})
        log_raw("faucet", f"CLAIM RESPONSE (HTTP {s})", d, C.G if s in (200,201) else C.R)
        return (True, d) if s in (200, 201) and (d.get("success") or d.get("reward")) else (False, d)

    def ptc_list(self):
        log("ptc", "fetching list...", C.B)
        d = self.g("/ptc")
        if isinstance(d, list):
            log("ptc", f"found {len(d)} ads", C.G)
            for i, ad in enumerate(d[:5]):
                log("ptc", f"  [{i}] id={ad.get('id')} type={ad.get('type')} provider={ad.get('provider')} reward={ad.get('viewer_reward')}", C.D)
        else:
            log("ptc", f"unexpected response type: {type(d)}", C.R)
        return d if isinstance(d, list) else []

    def ptc_verify(self, ad, ct, f):
        log("ptc", f"verify-start id={ad}", C.B)
        s, d = self.p(f"/ptc/verify-start/{ad}", {"captcha_token": ct, "fingerprint": f})
        log_raw("ptc", "VERIFY-START RESPONSE", d, C.G if s in (200,201) else C.R)
        return d.get("view_token") if s in (200, 201) else None

    def ptc_view(self, ad, vt):
        log("ptc", f"start-view id={ad}", C.B)
        s, d = self.p(f"/ptc/start-view/{ad}", {"view_token": vt})
        return d if s in (200, 201) else None

    def ptc_surf(self, ad):
        log("ptc", f"start-surf id={ad}", C.B)
        s, d = self.p(f"/ptc/start-surf/{ad}", {})
        return d if s in (200, 201) else None

    def ptc_claim(self, ad, f):
        log("ptc", f"claim id={ad}", C.B)
        s, d = self.p(f"/ptc/claim/{ad}", {"fingerprint": json.dumps(f)})
        log_raw("ptc", f"CLAIM RESPONSE (HTTP {s})", d, C.G if s in (200,201) else C.R)
        return (True, d) if s in (200, 201) else (False, d)

    def faucet_status(self):
        d = self.g("/faucet") or {}
        if d:
            log("faucet", f"status: time_left={d.get('time_left','?')}s", C.D)
        return d

    def short_list(self):
        log("shortlink", "fetching list...", C.B)
        d = self.g("/shortlinks")
        if isinstance(d, list):
            log("shortlink", f"found {len(d)} shortlinks", C.G)
        return d if isinstance(d, list) else []

    def short_bypass(self, shid, ct, f):
        log("shortlink", f"verify-start id={shid}", C.B)
        _, dv = self.p(f"/shortlinks/verify-start/{shid}", {"captcha_token": ct, "fingerprint": f})
        log_raw("shortlink", "VERIFY-START", dv, C.Y)
        if not (gtk := dv.get("generation_token")):
            log("shortlink", "no generation_token", C.R)
            return None

        self.sync()
        log("shortlink", f"generate-verified id={shid}", C.B)
        _, dg = self.p(f"/shortlinks/generate-verified/{shid}", {"generation_token": gtk, "fingerprint": f.get("device_id")})
        log_raw("shortlink", "GENERATE-VERIFIED", dg, C.Y)
        if not dg.get("shortened_url"):
            log("shortlink", "no shortened_url", C.R)
            return None

        time.sleep(5); self.sync()
        log("shortlink", f"claiming id={shid}", C.B)
        sc, dc = self.p("/shortlinks/claim", {"shortlink_id": shid, "fingerprint": f})
        log_raw("shortlink", f"CLAIM RESPONSE (HTTP {sc})", dc, C.G if sc in (200,201) else C.R)
        return dc if sc in (200, 201) else None

def solve_cap(c, tries=15):
    for attempt in range(tries):
        log("captcha", f"attempt {attempt+1}/{tries}", C.B)
        g = c.gen_captcha()
        if not g.get("bg_image"):
            log("captcha", "no bg_image, retrying...", C.Y)
            time.sleep(2); continue
        if (x := solve(g["bg_image"], g["piece_image"])) is None:
            log("captcha", "edge detection failed, retrying...", C.Y)
            time.sleep(1.5); continue
        log("captcha", f"detected x_pos={x}", C.G)
        time.sleep(random.randint(800, 2500) / 1000)
        t0 = int(time.time() * 1000)
        ok, d = c.verify_cap(g["token"], x, traj(x, t0), random.randint(800, 2500))
        if ok:
            log("captcha", f"verified! token={d.get('verified_token','?')[:30]}...", C.G)
            return d["verified_token"]
        log("captcha", f"verify failed: {d.get('message','unknown')}", C.R)
        time.sleep(1.5)
    log("captcha", "all attempts exhausted", C.R)
    return None

def do_ptc(c):
    for ad in [a for a in c.ptc_list() if a.get("type") == "manual"]:
        aid = ad.get("id")
        log("ptc", f"verifying {aid}", C.B)
        c.sync()
        if not (ct := solve_cap(c)): log("ptc", "captcha fail", C.R); continue
        if not (vt := c.ptc_verify(aid, ct, fp())): log("ptc", "verify fail", C.R); continue
        c.sync()
        if not (vd := c.ptc_view(aid, vt) or c.ptc_surf(aid)): log("ptc", "view fail", C.R); continue
        dur = (vd.get("ad") or {}).get("duration_seconds", ad.get("duration_seconds", 30))
        log("ptc", f"viewing {dur}s", C.Y)
        time.sleep(dur); c.sync()
        ok, d = c.ptc_claim(aid, fp())
        if ok:
            log("ptc", f"+{float(d.get('reward', 0) or 0)} COIN +{d.get('xp_earned', 0)} XP", C.G)
        else:
            log("ptc", f"claim fail: {d.get('message', '')}", C.R)
        time.sleep(random.uniform(2, 5))

def do_ptc_ext(c, w):
    ads = [a for a in c.ptc_list() if a.get("type") == "api" and a.get("provider") == "BitcoTasks"]
    if not ads: log("ptc-ext", "no external ads", C.D); return
    for ad in ads:
        title = (ad.get("title") or "?")[:24]
        log("ptc-ext", f"solving {title}", C.B)
        if BcttSolver(w).run(ad.get("url", "")):
            log("ptc-ext", f"+{float(ad.get('viewer_reward', 0) or 0)} COIN +{int(ad.get('xp_reward', 0) or 0)} XP", C.G)
        else:
            log("ptc-ext", "failed", C.R)
        time.sleep(random.uniform(1, 3))

def do_faucet(c):
    s = c.faucet_status()
    if (cd := int(s.get("time_left", 0))) > 0:
        log("faucet", f"cooldown {cd}s, skipping", C.D); return
    log("faucet", "solving captcha", C.B)
    c.sync()
    if not (ct := solve_cap(c)): log("faucet", "captcha fail", C.R); return
    ok, d = c.claim_faucet(ct, fp(), ix())
    if ok:
        log("faucet", f"+{float(d.get('reward', 0) or 0)} COIN +{d.get('xp_earned', 0)} XP", C.G)
    else:
        log("faucet", f"fail: {d.get('message', '')}", C.R)

def do_short(c):
    slinks = [l for l in c.short_list() if l.get("type") == "manual"]
    if not slinks: log("shortlink", "no direct shortlink", C.D); return
    for link in slinks:
        reward = int(link.get("reward", 0)); available = int(link.get("available", 0)); shid = int(link.get("id"))
        log("shortlink", f"id={shid} reward={reward} available={available}", C.B)
        if available <= 0: continue
        for i in range(available):
            if not (ct := solve_cap(c)): log("shortlink", "captcha fail", C.R); return
            c.sync()
            claim = c.short_bypass(shid, ct, fp())
            log("shortlink", f"id={shid} claim {i+1}/{available} {'done' if claim else 'fail'}", C.G if claim else C.R)

def main():
    # Log proxy info pertama kali
    log_proxy_info()

    e, pw, ak = load_cfg()
    c = Client()
    log("auth", "solving login captcha...", C.B)
    if not (ct := solve_cap(c)): log("auth", "login captcha fail", C.R); sys.exit(1)
    ok, name = c.login(e, pw, ct)
    if not ok: log("auth", f"login fail: {name}", C.R); sys.exit(1)
    log("auth", f"logged in as {name}", C.G)

    while True:
        do_short(c); do_ptc(c); do_ptc_ext(c, Waryono(ak)); do_faucet(c); time.sleep(5)

if __name__ == "__main__":
    main()
