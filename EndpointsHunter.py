#!/usr/bin/env python3
"""
EndpointsHunter Ultimate v4.0
✅ يستخرج الـ endpoints الكاملة مع query parameters
✅ VirusTotal API v3
✅ تحسين Wayback Machine لاستخراج كل البراميترات
✅ فلترة ذكية بدون حذف البراميترات المهمة
"""

import requests
import re
import sys
import os
import json
import time
import concurrent.futures
import urllib3
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from collections import defaultdict
from colorama import Fore, Style, init
import warnings
import queue
import threading

warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

# =========================
# CONFIGURATION
# =========================

VT_API_KEYS = [
    "",
    "",
    ""
]

OTX_API_KEY    = ""
URLSCAN_API_KEY = ""
GITHUB_TOKEN   = ""

TIMEOUT              = 5
MAX_RETRIES          = 2
USER_AGENT           = "EndpointsHunter/4.0"
OUTPUT_FILE          = "found_endpoints.txt"
JSON_OUTPUT          = "endpoints_detailed.json"
MAX_WORKERS          = 50
MAX_ENDPOINTS_TO_CHECK = 500

# =========================
# WORDLIST
# =========================
COMMON_PATHS = [
    "/admin", "/administrator", "/login", "/signin", "/auth", "/api", "/api/v1", "/api/v2",
    "/api/graphql", "/graphql", "/swagger", "/api-docs", "/openapi.json", "/console", "/dashboard",
    "/config", "/test", "/debug", "/status", "/health", "/robots.txt", "/sitemap.xml", "/.env",
    "/wp-admin", "/phpmyadmin", "/mysql", "/adminer", "/backup", "/backup.zip", "/db_backup",
    "/upload", "/uploads", "/images", "/static", "/assets", "/static/js", "/static/css",
    "/web.config", "/.git", "/.svn", "/error_log", "/access_log", "/logs", "/tmp",
    "/app.js", "/chunk.js", "/main.js", "/bundle.js", "/vendor.js",
    "/user", "/users", "/profile", "/settings", "/account", "/register", "/signup",
    "/forgot-password", "/reset", "/verify", "/oauth", "/token", "/logout",
    "/api/auth", "/api/users", "/api/login", "/api/admin", "/api/config",
    "/docs", "/doc", "/server-status", "/csrf", "/phpinfo.php",
    "/files", "/download", "/data", "/database", "/db", "/sql",
    "/shell", "/cmd", "/exec", "/install", "/setup",
    "/readme", "/changelog", "/security", "/privacy", "/terms",
    "/contact", "/about", "/faq", "/help", "/support",
    "/blog", "/news", "/media", "/css", "/js", "/fonts"
]

# =========================
# HELPERS
# =========================

def print_banner(text):
    print(f"\n{Fore.CYAN}{'='*90}")
    print(f"{Fore.CYAN}[+] {text}")
    print(f"{Fore.CYAN}{'='*90}{Style.RESET_ALL}")

def print_section(name):
    print(f"\n{Fore.BLUE}[+] {name}{Style.RESET_ALL}")

def print_success(msg):
    print(f" {Fore.GREEN}[+] {msg}{Style.RESET_ALL}")

def print_error(msg):
    print(f" {Fore.RED}[-] {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f" {Fore.YELLOW}[*] {msg}{Style.RESET_ALL}")


class Endpoint:
    """
    كلاس يمثل endpoint كامل مع path + params
    نفصل بين الاثنين للمقارنة والعرض
    """
    def __init__(self, path: str, params: dict = None, full_url: str = ""):
        self.path     = path        # /api/v1/user
        self.params   = params or {}  # {'id': ['123'], 'token': ['abc']}
        self.full_url = full_url    # URL أصلي للمرجع

    @property
    def full_path(self) -> str:
        """المسار الكامل مع البراميترات"""
        if self.params:
            return f"{self.path}?{urlencode(self.params, doseq=True)}"
        return self.path

    @property
    def param_keys(self) -> list:
        """أسماء البراميترات فقط بدون قيم"""
        return sorted(self.params.keys())

    def dedup_key(self) -> str:
        """
        مفتاح إزالة التكرار الذكي:
        - نفس الـ path + نفس أسماء البراميترات (بغض النظر عن القيم) = تكرار
        - /api?id=1 و /api?id=2 يُعتبران نفس الـ endpoint
        - لكن /api?id=1 و /api?token=abc مختلفان
        """
        return f"{self.path}?{','.join(self.param_keys)}" if self.params else self.path

    def __repr__(self):
        return f"Endpoint({self.full_path})"


def is_valid_path(path: str) -> bool:
    """التحقق من صحة المسار"""
    if not path or not path.startswith('/'):
        return False
    if path == '/':
        return False
    first_segment = path.lstrip('/').split('/')[0]
    if '.' in first_segment and not first_segment.startswith('.'):
        return False  # subdomain وليس path
    if len(path.rstrip('/')) < 2:
        return False
    return True


def parse_endpoint_from_url(raw_url: str, target_domain: str) -> Endpoint | None:
    """
    ✅ الدالة الجديدة — تستخرج path + params كاملاً
    لا تحذف query string بعد الآن
    """
    if not raw_url:
        return None

    try:
        raw_url = raw_url.strip()

        # تأكد أنه ينتمي لنفس الدومين
        if not is_subdomain_match(raw_url, target_domain):
            return None

        # parse
        if '://' in raw_url:
            parsed = urlparse(raw_url)
        elif raw_url.startswith('//'):
            parsed = urlparse('https:' + raw_url)
        else:
            parsed = urlparse('https://' + target_domain + '/' + raw_url.lstrip('/'))

        path = parsed.path or '/'

        # normalize
        if len(path) > 1:
            path = path.rstrip('/')

        # استخراج query params
        params = parse_qs(parsed.query, keep_blank_values=False)

        # المسار يجب أن يكون صالحاً — لكن / مع params مقبولة
        if path == '/' and not params:
            return None

        if path != '/' and not is_valid_path(path):
            return None

        return Endpoint(path=path, params=params, full_url=raw_url)

    except Exception:
        return None


def is_subdomain_match(url: str, target_domain: str) -> bool:
    try:
        if '://' in url:
            netloc = urlparse(url).netloc
        elif url.startswith('//'):
            netloc = url[2:].split('/')[0]
        else:
            netloc = url.split('/')[0]

        netloc = netloc.split(':')[0].lower()
        target = target_domain.lower()
        return netloc == target or netloc.endswith('.' + target)
    except:
        return False


def retry_request(func, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(0.3)
    return None


def deduplicate_endpoints(endpoints: list[Endpoint]) -> list[Endpoint]:
    """
    إزالة التكرار الذكية:
    - نحتفظ بمثال واحد لكل (path + param_keys)
    - نفضّل الـ endpoint الذي يملك قيم براميترات غير فارغة
    """
    seen = {}
    for ep in endpoints:
        key = ep.dedup_key()
        if key not in seen:
            seen[key] = ep
        else:
            # إذا النسخة الجديدة لها قيم أكثر — احتفظ بها
            if len(str(ep.params)) > len(str(seen[key].params)):
                seen[key] = ep
    return list(seen.values())


# =========================
# ENDPOINT CHECKING
# =========================

def check_endpoint_live(endpoint: Endpoint, domain: str, protocol: str = "https", result_queue=None) -> dict:
    result = {
        'path':     endpoint.path,
        'params':   endpoint.params,
        'full_path': endpoint.full_path,
        'status':   'ERR',
        'length':   0,
        'title':    ''
    }

    try:
        url = f"{protocol}://{domain}{endpoint.full_path}"
        r   = requests.get(url, headers={'User-Agent': USER_AGENT},
                           timeout=TIMEOUT, verify=False, allow_redirects=True)

        result['status'] = r.status_code
        result['length'] = len(r.content)

        m = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
        if m:
            result['title'] = m.group(1).strip()[:100]

    except requests.exceptions.Timeout:
        result['status'] = 'TIMEOUT'
    except requests.exceptions.ConnectionError:
        result['status'] = 'CONN_ERR'
    except Exception:
        pass

    if result_queue and result['status'] not in ['ERR', 'TIMEOUT', 'CONN_ERR']:
        result_queue.put(result)

    return result


# =========================
# DATA SOURCES
# =========================

def fetch_wayback(domain: str) -> list[Endpoint]:
    """
    Wayback Machine ✅ محسّن:
    - يجلب URLs مع براميترات كاملة (collapse=urlkey يجمع نفس الـ path معاً)
    - نستخدم fl=original للحصول على الـ URL الأصلي مع query string
    """
    endpoints = []
    try:
        # ✅ أزلنا collapse=urlkey حتى نحصل على كل URLs مختلفة (بما فيها بمعاملات مختلفة)
        url = (
            f"https://web.archive.org/cdx/search/cdx"
            f"?url={domain}/*"
            f"&output=json"
            f"&fl=original"           # الـ URL الكامل مع query string
            f"&limit=5000"
            f"&filter=statuscode:200" # فقط الصفحات التي استُجيب لها
        )

        resp = retry_request(requests.get, url, timeout=40)
        if resp and resp.status_code == 200:
            data = resp.json()
            for item in data[1:]:
                raw_url = item[0] if isinstance(item, list) else item
                ep = parse_endpoint_from_url(raw_url, domain)
                if ep:
                    endpoints.append(ep)

    except Exception as e:
        print_error(f"Wayback error: {e}")

    return endpoints


def fetch_wayback_params(domain: str) -> list[Endpoint]:
    """
    ✅ جديد: Wayback Machine بحث خاص بالـ URLs التي تحتوي '?'
    يركز على استخراج كل query parameters موجودة
    """
    endpoints = []
    try:
        url = (
            f"https://web.archive.org/cdx/search/cdx"
            f"?url={domain}/*%3F*"   # * يلي ? = أي query string
            f"&output=json"
            f"&fl=original"
            f"&limit=3000"
        )

        resp = retry_request(requests.get, url, timeout=40)
        if resp and resp.status_code == 200:
            data = resp.json()
            for item in data[1:]:
                raw_url = item[0] if isinstance(item, list) else item
                ep = parse_endpoint_from_url(raw_url, domain)
                if ep and ep.params:  # فقط اللي فيها params
                    endpoints.append(ep)

    except Exception as e:
        print_error(f"Wayback params error: {e}")

    return endpoints


def fetch_otx(domain: str) -> list[Endpoint]:
    """AlienVault OTX"""
    endpoints = []
    if not OTX_API_KEY:
        return endpoints

    try:
        for page in range(1, 10):
            url = f"https://otx.alienvault.com/api/v1/indicators/hostname/{domain}/url_list?limit=200&page={page}"
            headers = {"X-OTX-API-KEY": OTX_API_KEY}

            resp = retry_request(requests.get, url, headers=headers, timeout=15)
            if not resp or resp.status_code != 200:
                break

            data  = resp.json()
            items = data.get('url_list', [])
            if not items:
                break

            for item in items:
                raw_url = item.get('url', '')
                ep = parse_endpoint_from_url(raw_url, domain)
                if ep:
                    endpoints.append(ep)

            time.sleep(0.3)

    except Exception:
        pass

    return endpoints


def fetch_vt(domain: str) -> list[Endpoint]:
    """
    VirusTotal ✅ محسّن:
    - يستخدم API v3 بدلاً من v2 القديم
    - يستخرج URLs مع query parameters كاملة
    """
    endpoints = []

    for key in VT_API_KEYS:
        try:
            # ✅ API v3 — أحدث وأشمل
            url     = f"https://www.virustotal.com/api/v3/domains/{domain}/urls?limit=40"
            headers = {"x-apikey": key}

            resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code in [401, 403]:
                continue

            if resp.status_code == 200:
                data = resp.json()

                for item in data.get('data', []):
                    attrs   = item.get('attributes', {})
                    raw_url = attrs.get('url', '')
                    if raw_url:
                        ep = parse_endpoint_from_url(raw_url, domain)
                        if ep:
                            endpoints.append(ep)

                # pagination
                cursor = data.get('meta', {}).get('cursor')
                while cursor and len(endpoints) < 500:
                    next_url  = f"https://www.virustotal.com/api/v3/domains/{domain}/urls?limit=40&cursor={cursor}"
                    next_resp = requests.get(next_url, headers=headers, timeout=15)
                    if next_resp.status_code != 200:
                        break
                    next_data = next_resp.json()
                    for item in next_data.get('data', []):
                        attrs   = item.get('attributes', {})
                        raw_url = attrs.get('url', '')
                        if raw_url:
                            ep = parse_endpoint_from_url(raw_url, domain)
                            if ep:
                                endpoints.append(ep)
                    cursor = next_data.get('meta', {}).get('cursor')
                    time.sleep(0.5)

                if endpoints:
                    break

        except Exception:
            continue

    # ✅ fallback: API v2 إذا v3 فشل
    if not endpoints:
        for key in VT_API_KEYS:
            try:
                url  = f"https://www.virustotal.com/vtapi/v2/domain/report?apikey={key}&domain={domain}"
                resp = requests.get(url, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('response_code') == 1:
                        all_urls = data.get('detected_urls', []) + data.get('undetected_urls', [])
                        for item in all_urls:
                            raw_url = ""
                            if isinstance(item, dict):
                                raw_url = item.get('url', '')
                            elif isinstance(item, list) and item:
                                raw_url = item[0]
                            if raw_url:
                                ep = parse_endpoint_from_url(raw_url, domain)
                                if ep:
                                    endpoints.append(ep)
                        if endpoints:
                            break
            except Exception:
                continue

    return endpoints


def fetch_urlscan(domain: str) -> list[Endpoint]:
    """URLScan.io"""
    endpoints = []
    if not URLSCAN_API_KEY:
        return endpoints

    try:
        headers = {"API-Key": URLSCAN_API_KEY}
        url     = f"https://urlscan.io/api/v1/search/?q=page.domain:{domain}&size=100"

        resp = retry_request(requests.get, url, headers=headers, timeout=20)
        if resp and resp.status_code == 200:
            data = resp.json()
            for result in data.get('results', []):
                task    = result.get('task', {})
                page    = result.get('page', {})
                raw_url = task.get('url') or page.get('url')
                if raw_url:
                    ep = parse_endpoint_from_url(raw_url, domain)
                    if ep:
                        endpoints.append(ep)

    except Exception:
        pass

    return endpoints


def fetch_commoncrawl(domain: str) -> list[Endpoint]:
    """CommonCrawl"""
    endpoints = []
    try:
        url  = f"http://index.commoncrawl.org/CC-MAIN-2024-10-index?url={domain}/*&output=json&limit=1000"
        resp = requests.get(url, timeout=30, stream=True)

        if resp.status_code == 200:
            for line in resp.iter_lines(decode_unicode=True):
                if len(endpoints) >= 800:
                    break
                if line:
                    try:
                        record  = json.loads(line)
                        raw_url = record.get('url', '')
                        ep      = parse_endpoint_from_url(raw_url, domain)
                        if ep:
                            endpoints.append(ep)
                    except:
                        continue
    except:
        pass

    return endpoints


def fetch_github_paths(domain: str) -> list[Endpoint]:
    """GitHub — يستخرج مسارات من الكود المصدري"""
    endpoints = []
    if not GITHUB_TOKEN:
        return endpoints

    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        query = f'"{domain}" in:file'
        url   = f"https://api.github.com/search/code?q={query}&per_page=30"

        resp = retry_request(requests.get, url, headers=headers, timeout=15)
        if not resp or resp.status_code != 200:
            return endpoints

        data         = resp.json()
        path_pattern = re.compile(r'(?:"|\'|`)(/[a-zA-Z0-9_\-/\.]+)(?:"|\'|`)')

        for item in data.get('items', [])[:10]:
            try:
                file_url  = item.get('url', '')
                file_resp = requests.get(file_url, headers=headers, timeout=10)
                if file_resp.status_code != 200:
                    continue

                file_data = file_resp.json()
                import base64
                content   = base64.b64decode(file_data.get('content', '')).decode('utf-8', errors='ignore')

                for match in path_pattern.findall(content):
                    if is_valid_path(match):
                        endpoints.append(Endpoint(path=match))

                time.sleep(0.5)
            except:
                continue

    except Exception:
        pass

    return endpoints


# =========================
# ACTIVE FUZZER
# =========================

def active_fuzzer(domain: str) -> list[dict]:
    found = []
    print_info(f"Fuzzing {len(COMMON_PATHS)} paths...")

    rq = queue.Queue()

    def display():
        while True:
            try:
                res = rq.get(timeout=0.1)
                if res is None:
                    break
                color = Fore.GREEN if res['status'] == 200 else Fore.YELLOW
                print(f"  {res['full_path']} ({color}{res['status']}{Style.RESET_ALL}) [{res['length']}b]")
                found.append(res)
            except queue.Empty:
                continue

    t = threading.Thread(target=display, daemon=True)
    t.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        futures = [ex.submit(check_endpoint_live, Endpoint(p), domain, "https", rq) for p in COMMON_PATHS]
        concurrent.futures.wait(futures)

    rq.put(None)
    t.join()
    return found


# =========================
# OUTPUT
# =========================

def save_results(all_results: list[dict], domain: str):
    valid = [r for r in all_results if r['status'] not in ['ERR', 'TIMEOUT', 'CONN_ERR']]

    # احفظ full_path (مع براميترات)
    unique_paths = sorted(set(r['full_path'] for r in valid))

    with open(OUTPUT_FILE, "w") as f:
        for p in unique_paths:
            f.write(f"{p}\n")

    print(f"\n{Fore.GREEN}[*] {len(unique_paths)} unique endpoints saved to {OUTPUT_FILE}{Style.RESET_ALL}")

    json_data = {
        'domain':         domain,
        'scan_time':      datetime.now().isoformat(),
        'total_endpoints': len(valid),
        'unique_paths':   len(unique_paths),
        'endpoints':      valid
    }

    with open(JSON_OUTPUT, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"{Fore.GREEN}[*] Detailed report: {JSON_OUTPUT}{Style.RESET_ALL}")


# =========================
# MAIN
# =========================

def main():
    print_banner("EndpointsHunter Ultimate v4.0 — Full Params Extraction")

    domain = input(f"{Fore.CYAN}Enter domain: {Style.RESET_ALL}").strip()
    if not domain:
        sys.exit(1)

    domain = domain.replace('http://', '').replace('https://', '').split('/')[0]

    print(f"\n{Fore.YELLOW}[*] Target: {domain}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[*] Step 1: Deep Harvesting (with parameters)...{Style.RESET_ALL}")

    # ── تشغيل جميع المصادر بالتوازي ────────────────────────────────
    collectors = [
        (fetch_wayback,       "Wayback Machine"),
        (fetch_wayback_params,"Wayback Params"),   # ✅ جديد
        (fetch_commoncrawl,   "CommonCrawl"),
        (fetch_otx,           "AlienVault OTX"),
        (fetch_vt,            "VirusTotal v3"),    # ✅ محسّن
        (fetch_urlscan,       "URLScan"),
        (fetch_github_paths,  "GitHub (code)"),
    ]

    all_raw_endpoints: list[Endpoint] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        future_to_source = {
            executor.submit(func, domain): name
            for func, name in collectors
        }

        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                eps   = future.result()
                count = len(eps)
                all_raw_endpoints.extend(eps)

                color = Fore.GREEN if count > 0 else Fore.LIGHTBLACK_EX
                print(f"  {color}[+] {source}: {count} endpoints found{Style.RESET_ALL}")

            except Exception as e:
                print_error(f"{source}: {e}")

    # ── إزالة التكرار الذكية ────────────────────────────────────────
    deduped = deduplicate_endpoints(all_raw_endpoints)

    # ── إحصاء البراميترات ───────────────────────────────────────────
    with_params    = [ep for ep in deduped if ep.params]
    without_params = [ep for ep in deduped if not ep.params]

    print(f"\n{Fore.GREEN}[*] Total unique endpoints: {len(deduped)}{Style.RESET_ALL}")
    print(f"    {Fore.CYAN}├─ With parameters:    {len(with_params)}{Style.RESET_ALL}")
    print(f"    {Fore.CYAN}└─ Without parameters: {len(without_params)}{Style.RESET_ALL}")

    if not deduped:
        print(f"\n{Fore.RED}[-] No endpoints found. Switching to active fuzzing...{Style.RESET_ALL}")
        fuzzed = active_fuzzer(domain)
        if fuzzed:
            save_results(fuzzed, domain)
        else:
            print(f"{Fore.RED}[-] Nothing found.{Style.RESET_ALL}")
        print_banner("Scan Finished")
        return

    # ── ترتيب الأولويات ─────────────────────────────────────────────
    priority_keywords = ['/api', '/graphql', '/admin', '/login', '/auth',
                         '/config', '/swagger', '/v1', '/v2', '/token']

    priority_eps = [ep for ep in deduped if any(kw in ep.path.lower() for kw in priority_keywords)]
    other_eps    = [ep for ep in deduped if ep not in priority_eps]

    if len(deduped) > MAX_ENDPOINTS_TO_CHECK:
        print_info(f"Checking {MAX_ENDPOINTS_TO_CHECK} prioritized out of {len(deduped)}...")
        endpoints_to_check = priority_eps[:300] + other_eps[:MAX_ENDPOINTS_TO_CHECK - 300]
    else:
        print_info(f"Checking all {len(deduped)} endpoints...")
        endpoints_to_check = deduped

    # ── Live Checking ────────────────────────────────────────────────
    print(f"\n{Fore.YELLOW}[*] Step 2: Live Endpoint Checking...{Style.RESET_ALL}\n")

    valid_results = []
    rq            = queue.Queue()
    checked       = 0
    lock          = threading.Lock()

    def display_live():
        nonlocal checked
        while True:
            try:
                res = rq.get(timeout=0.1)
                if res is None:
                    break

                with lock:
                    valid_results.append(res)
                    checked += 1
                    n = checked

                if res['status'] == 200:
                    color = Fore.GREEN
                elif res['status'] == 403:
                    color = Fore.YELLOW
                elif res['status'] == 404:
                    color = Fore.LIGHTBLACK_EX
                else:
                    color = Fore.CYAN

                title = f" — {res['title'][:50]}" if res.get('title') else ""
                print(f"  [{n}/{len(endpoints_to_check)}] {res['full_path']} "
                      f"({color}{res['status']}{Style.RESET_ALL}) [{res['length']}b]{title}")

            except queue.Empty:
                continue

    display_thread = threading.Thread(target=display_live, daemon=True)
    display_thread.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_endpoint_live, ep, domain, "https", rq)
                   for ep in endpoints_to_check]
        concurrent.futures.wait(futures)

    rq.put(None)
    display_thread.join()

    print(f"\n{Fore.GREEN}[*] Live check done: {len(valid_results)} endpoints responded{Style.RESET_ALL}")

    if valid_results:
        save_results(valid_results, domain)

        # ── ملخص البراميترات المكتشفة ────────────────────────────────
        params_found = {r['full_path']: list(r['params'].keys())
                        for r in valid_results if r.get('params')}

        if params_found:
            print(f"\n{Fore.CYAN}[+] Endpoints with Parameters ({len(params_found)}):{Style.RESET_ALL}")
            for fp, keys in list(params_found.items())[:20]:
                print(f"  {Fore.YELLOW}{fp}{Style.RESET_ALL}  →  params: {', '.join(keys)}")
            if len(params_found) > 20:
                print(f"  ... and {len(params_found) - 20} more (see {JSON_OUTPUT})")

    # ── إحصاء Status Codes ───────────────────────────────────────────
    status_counts = defaultdict(int)
    for res in valid_results:
        status_counts[res['status']] += 1

    if status_counts:
        print(f"\n{Fore.CYAN}[+] Status Code Summary:{Style.RESET_ALL}")
        for status, count in sorted(status_counts.items()):
            color = Fore.GREEN if status == 200 else Fore.YELLOW
            print(f"  {color}{status}: {count}{Style.RESET_ALL}")

    print_banner("Scan Finished ✓")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.RED}[!] Interrupted{Style.RESET_ALL}")
        sys.exit(0)
