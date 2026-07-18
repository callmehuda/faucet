import requests, base64, hashlib, json, math, random, re, string, sys, time
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
    print(f"{color}[{tag}]{C.X} {msg}")

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

# FIX 1: Perbaikan Unpacking Dictionary via Opsi B (Singkat & Rapi)
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
            d = requests.post("https://api.waryono.my.id/in.php",
                json={"apikey": self._k, "methods": "bitcocaptcha", "type": "canvas", "body": body, "json": 1},
                timeout=30).json()
            if d.get("status") != 1 or not (tid := d.get("request")): return None
            for _ in range(90):
                time.sleep(4)
                r = requests.get("https://api.waryono.my.id/res.php",
                    params={"apikey": self._k, "id": tid, "action": "get", "json": 1}, timeout=30).json()
                if r.get("status") == 1: return r.get("request")
                if "NOT_READY" not in str(r.get("request", "")).upper(): return None
        except: pass
        return None

class BcttSolver:
    def __init__(self, w):
        self._w = w; self._s = requests.Session()
        self._ua = BCTT_UA

    # FIX 2: Otomatisasi URL builder anti "No scheme supplied"
    def _url(self, p):
        if not p: return BCTT_HOST
        if p.startswith("http"): return p
        return f"{BCTT_HOST.rstrip('/')}/{p.lstrip('/')}"

    def _fetch_site(self, url, ref):
        if not ref: return "none"
        try: return "same-origin" if urlparse(url).netloc == urlparse(ref).netloc else "cross-site"
        except: return "none"

    # FIX 3: Penyelarasan Headers murni dari versi Bot yang bekerja
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
        try: return self._s.get(actual, headers=h, timeout=30).text
        except: return ""

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
        try: return self._s.post(actual, data=data, headers=h, timeout=30).json()
        except: return {}

    def run(self, url, tmr=5):
        try:
            start = time.time()
            page0 = self._get(url)
            if not (m := re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", page0)): return False
            dest = m.group(1)
            
            if "Forbidden" in self._get(dest, ref=url): return False
            self._post(dest, {"action": "start_view"}, ref=dest)
            
            page = self._get(dest, ref=dest)
            if "Forbidden" in page: return False
            if not (p := self._params(page, tmr)): return False
            if not (src := re.search(r'<script[^>]+src=["\']([^"\']*captcha2/[^"\']*)["\']', page)): return False
            
            js = self._get(src.group(1), ref=dest)
            if not (fjs := self._parse_js(js)): return False
            
            m2 = re.search(r'fetch\("([^"]+captcha[^"]+\.js\?action=captcha)"', js)
            ep = m2.group(1) if m2 else src.group(1)
            
            cap = self._post(ep, {"t": int(time.time() * 1000), "r": random.random()}, ref=dest)
            if not cap.get("options") or not cap.get("pixel"): return False
            if not (sol := self._solve(cap)): return False
            
            pl = self._payload(fjs, sol)
            d = self._post(pl["url"], pl["data"], ref=dest)
            if not (tok := d.get(fjs["cc_ver"])): return False
            
            if (wait := p["timer"] - (time.time() - start)) > 0: time.sleep(math.ceil(wait))
            return self._submit(fjs, p, tok, dest)
        except Exception as e:
            log("bctt", f"error: {e}", C.R); return False

    def _val(self, html, name):
        for pat in [rf'name=["\']?{re.escape(name)}["\']?\s+value=["\']([^"\']*)["\']',
                    rf'value=["\']([^"\']*)["\'].*?name=["\']?{re.escape(name)}["\']?',
                    rf"var\s+{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]"]:
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

    # FIX 4: Fleksibilitas Regex Ekstraksi JavaScript Tingkat Tinggi (Anti Gagal Parse)
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
        return d.get("status") == 200

class Client:
    def __init__(self):
        self._s = requests.Session()
        self._s.headers.update({"Accept": "application/json", "User-Agent": UA,
                                "Origin": "https://cryptifo.com", "Referer": "https://cryptifo.com/",
                                "Accept-Encoding": "gzip, deflate"})
        self._tok = None

    def _req(self, m, p, data=None):
        h = {"Authorization": f"Bearer {self._tok}"} if self._tok else {}
        try:
            r = self._s.request(m, f"{BASE}{p}", json=data, headers=h, timeout=30)
            try: return r.status_code, r.json()
            except: return r.status_code, {}
        except Exception as e:
            log("net", str(e), C.R); return 0, {}

    def g(self, p):
        s, d = self._req("GET", p)
        return d if s == 200 else None

    def p(self, p, data):
        return self._req("POST", p, data)

    def login(self, em, pw, ct):
        s, d = self.p("/login", {"email": em, "password": pw, "captcha_token": ct})
        if s in (200, 201) and d.get("token"):
            self._tok = d["token"]; return True, d.get("user", {}).get("name", "?")
        return False, d.get("message", f"HTTP {s}")

    def sync(self):
        return self.p("/system/sync-status", {"bw": 1, "bh": 1, "nonce": None})[1]

    def gen_captcha(self):
        return self.g("/captcha/generate") or {}

    def verify_cap(self, tok, xp, tr, rt):
        _, d = self.p("/captcha/verify", {"token": tok, "x_pos": xp, "trajectory": tr, "reaction_time": rt})
        return (True, d) if d.get("success") and d.get("verified_token") else (False, d)

    def claim_faucet(self, ct, f, i):
        s, d = self.p("/faucet/claim", {"captcha_token": ct, "fingerprint": f, "interaction": i})
        return (True, d) if s in (200, 201) and (d.get("success") or d.get("reward")) else (False, d)

    def ptc_list(self):
        return d if isinstance(d := self.g("/ptc"), list) else []

    def ptc_verify(self, ad, ct, f):
        s, d = self.p(f"/ptc/verify-start/{ad}", {"captcha_token": ct, "fingerprint": f})
        return d.get("view_token") if s in (200, 201) else None

    def ptc_view(self, ad, vt):
        s, d = self.p(f"/ptc/start-view/{ad}", {"view_token": vt})
        return d if s in (200, 201) else None

    def ptc_surf(self, ad):
        s, d = self.p(f"/ptc/start-surf/{ad}", {})
        return d if s in (200, 201) else None

    def ptc_claim(self, ad, f):
        s, d = self.p(f"/ptc/claim/{ad}", {"fingerprint": json.dumps(f)})
        return (True, d) if s in (200, 201) else (False, d)

    def faucet_status(self):
        return self.g("/faucet") or {}

    def short_list(self):
        return d if isinstance(d := self.g("/shortlinks"), list) else []

    def short_bypass(self, shid, ct, f):
        _, dv = self.p(f"/shortlinks/verify-start/{shid}", {"captcha_token": ct, "fingerprint": f})
        if not (gtk := dv.get("generation_token")): return None
        self.sync()
        _, dg = self.p(f"/shortlinks/generate-verified/{shid}", {"generation_token": gtk, "fingerprint": f.get("device_id")})
        if not dg.get("shortened_url"): return None
        time.sleep(5); self.sync()
        sc, dc = self.p("/shortlinks/claim", {"shortlink_id": shid, "fingerprint": f})
        return dc if sc in (200, 201) else None

def solve_cap(c, tries=15):
    for _ in range(tries):
        g = c.gen_captcha()
        if not g.get("bg_image"): time.sleep(2); continue
        if (x := solve(g["bg_image"], g["piece_image"])) is None: time.sleep(1.5); continue
        time.sleep(random.randint(800, 2500) / 1000)
        t0 = int(time.time() * 1000)
        ok, d = c.verify_cap(g["token"], x, traj(x, t0), random.randint(800, 2500))
        if ok: return d["verified_token"]
        time.sleep(1.5)
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
