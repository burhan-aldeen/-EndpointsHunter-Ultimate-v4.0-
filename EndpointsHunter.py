#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          EndpointsHunter Ultimate v5.0  —  by @Burhan_ALDeem                 ║
║  ✅ Multi-source harvesting   ✅ Smart dedup   ✅ Full params extraction     ║
║  ✅ Organized output per source  ✅ Raw section  ✅ Extended wordlist        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import re
import sys
import os
import json
import time
import base64
import concurrent.futures
import urllib3
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from collections import defaultdict
from colorama import Fore, Back, Style, init
import warnings
import queue
import threading

warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

# ═══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

VT_API_KEYS = [
    "",
    "",
    "",
]

OTX_API_KEY     = ""
URLSCAN_API_KEY = ""
GITHUB_TOKEN    = ""

TIMEOUT               = 6
MAX_RETRIES           = 2
USER_AGENT            = "Mozilla/5.0 (EndpointsHunter/5.0)"
OUTPUT_FILE           = "found_endpoints.txt"
JSON_OUTPUT           = "endpoints_detailed.json"
MAX_WORKERS           = 60
MAX_ENDPOINTS_TO_CHECK = 600

# ═══════════════════════════════════════════════════════════════════
#  EXTENDED WORDLIST  —  covers all major web technologies
# ═══════════════════════════════════════════════════════════════════

COMMON_PATHS = [
    # ── Auth / Session ─────────────────────────────────────────────
    "/login", "/signin", "/sign-in", "/logout", "/sign-out", "/register", "/signup",
    "/sign-up", "/auth", "/auth/login", "/auth/register", "/auth/logout",
    "/auth/callback", "/auth/token", "/auth/refresh", "/auth/verify",
    "/oauth", "/oauth2", "/oauth/authorize", "/oauth/token", "/oauth/callback",
    "/sso", "/sso/login", "/saml", "/saml/acs", "/saml/metadata",
    "/forgot-password", "/reset-password", "/change-password",
    "/2fa", "/mfa", "/otp", "/verify-email", "/confirm",

    # ── API Roots ──────────────────────────────────────────────────
    "/api", "/api/v1", "/api/v2", "/api/v3", "/api/v4",
    "/api/internal", "/api/private", "/api/public", "/api/external",
    "/api/auth", "/api/login", "/api/logout", "/api/register",
    "/api/user", "/api/users", "/api/me", "/api/profile",
    "/api/admin", "/api/config", "/api/settings", "/api/status",
    "/api/health", "/api/ping", "/api/version", "/api/info",
    "/api/search", "/api/data", "/api/export", "/api/import",
    "/api/upload", "/api/download", "/api/token", "/api/keys",
    "/api/webhooks", "/api/events", "/api/notifications",
    "/api/payment", "/api/billing", "/api/orders",

    # ── GraphQL ────────────────────────────────────────────────────
    "/graphql", "/graphiql", "/graphql/console", "/graphql/playground",
    "/api/graphql", "/v1/graphql", "/query", "/gql",

    # ── REST versioning ────────────────────────────────────────────
    "/v1", "/v2", "/v3", "/v4", "/rest", "/rest/v1", "/rest/v2",
    "/service", "/services", "/endpoint", "/rpc",

    # ── Admin / Management ─────────────────────────────────────────
    "/admin", "/administrator", "/admin/login", "/admin/dashboard",
    "/admin/users", "/admin/config", "/admin/settings", "/admin/panel",
    "/manage", "/management", "/manager", "/control", "/panel",
    "/cp", "/controlpanel", "/console", "/dashboard",
    "/superuser", "/superadmin", "/root",

    # ── Documentation / Dev ────────────────────────────────────────
    "/swagger", "/swagger-ui", "/swagger-ui.html", "/swagger/index.html",
    "/api-docs", "/api/docs", "/docs", "/doc",
    "/openapi.json", "/openapi.yaml", "/openapi",
    "/redoc", "/api/redoc", "/apidoc",
    "/raml", "/wsdl", "/wadl",
    "/spec", "/schema", "/specification",

    # ── Health / Monitoring ────────────────────────────────────────
    "/health", "/healthz", "/health/live", "/health/ready",
    "/ping", "/status", "/ready", "/alive",
    "/metrics", "/actuator", "/actuator/health", "/actuator/info",
    "/actuator/env", "/actuator/beans", "/actuator/mappings",
    "/monitor", "/monitoring", "/stats", "/statistics",
    "/server-status", "/server-info",

    # ── Config / Environment ───────────────────────────────────────
    "/.env", "/.env.local", "/.env.dev", "/.env.prod", "/.env.staging",
    "/.env.example", "/.env.backup",
    "/config", "/config.json", "/config.yml", "/config.yaml",
    "/configuration", "/settings", "/app.config",
    "/application.yml", "/application.properties",
    "/web.config", "/appsettings.json",

    # ── Files / Uploads ────────────────────────────────────────────
    "/upload", "/uploads", "/file", "/files", "/media",
    "/download", "/downloads", "/attachment", "/attachments",
    "/image", "/images", "/img", "/photo", "/photos", "/avatar",
    "/document", "/documents", "/pdf",
    "/export", "/import", "/backup", "/restore",

    # ── Static Assets ──────────────────────────────────────────────
    "/static", "/assets", "/public",
    "/js", "/css", "/fonts", "/icons",
    "/static/js", "/static/css",
    "/dist", "/build", "/bundle",
    "/app.js", "/main.js", "/bundle.js", "/vendor.js",
    "/chunk.js", "/runtime.js", "/app.min.js",
    "/webpack-stats.json", "/asset-manifest.json",
    "/manifest.json", "/service-worker.js",

    # ── User / Profile ─────────────────────────────────────────────
    "/user", "/users", "/profile", "/me", "/account", "/accounts",
    "/member", "/members", "/customer", "/customers",
    "/settings", "/preferences", "/notifications",
    "/subscription", "/subscriptions", "/billing",

    # ── Search ─────────────────────────────────────────────────────
    "/search", "/find", "/query", "/lookup", "/filter",
    "/api/search", "/search/api",

    # ── Database / Backend leak ────────────────────────────────────
    "/db", "/database", "/sql", "/mysql", "/postgres", "/mongo",
    "/phpmyadmin", "/adminer", "/adminer.php",
    "/pgadmin", "/myadmin",
    "/redis", "/elastic", "/elasticsearch",

    # ── Debug / Testing ────────────────────────────────────────────
    "/debug", "/test", "/testing", "/dev", "/development",
    "/staging", "/sandbox", "/preview",
    "/phpinfo.php", "/phpinfo", "/info.php",
    "/trace", "/tracing", "/profiler",

    # ── Payments ──────────────────────────────────────────────────
    "/payment", "/payments", "/checkout", "/cart", "/order", "/orders",
    "/invoice", "/invoices", "/billing", "/stripe", "/paypal",
    "/webhook", "/webhooks", "/ipn",

    # ── CMS / Platforms ───────────────────────────────────────────
    "/wp-admin", "/wp-login.php", "/wp-json", "/wp-content",
    "/wordpress", "/wp",
    "/drupal", "/joomla", "/magento",
    "/typo3", "/umbraco", "/craft",
    "/ghost", "/strapi", "/directus", "/contentful",
    "/laravel", "/django", "/rails", "/flask",
    "/admin/login.php", "/administrator/index.php",

    # ── Cloud / Infrastructure ────────────────────────────────────
    "/.well-known/security.txt", "/.well-known/assetlinks.json",
    "/.well-known/apple-app-site-association",
    "/robots.txt", "/sitemap.xml", "/sitemap.json",
    "/.htaccess", "/.htpasswd",
    "/.git", "/.git/config", "/.git/HEAD",
    "/.svn", "/.svn/entries",
    "/crossdomain.xml", "/clientaccesspolicy.xml",

    # ── Logs / Leak ───────────────────────────────────────────────
    "/log", "/logs", "/error_log", "/access_log", "/debug.log",
    "/storage/logs/laravel.log",
    "/var/log", "/tmp", "/temp",
    "/error", "/errors", "/exception",

    # ── Security / Reports ────────────────────────────────────────
    "/security", "/csrf", "/token", "/nonce",
    "/report", "/reports", "/audit", "/audit-log",

    # ── Node.js / JS frameworks ───────────────────────────────────
    "/node_modules", "/.npmrc", "/package.json",
    "/yarn.lock", "/package-lock.json",
    "/next", "/_next", "/_next/data",
    "/nuxt", "/_nuxt",
    "/socket.io", "/socket",

    # ── Python / Django / Flask ───────────────────────────────────
    "/admin/", "/django-admin", "/__debug__",
    "/api/schema", "/api/schema/", "/__schema__",

    # ── Java / Spring ─────────────────────────────────────────────
    "/actuator", "/actuator/env", "/jolokia",
    "/spring", "/struts",
    "/servlet", "/faces", "/jsf",

    # ── Ruby / Rails ──────────────────────────────────────────────
    "/rails/info", "/rails/info/properties",
    "/rails/mailers", "/rails/conductors",

    # ── PHP ───────────────────────────────────────────────────────
    "/index.php", "/home.php", "/about.php",
    "/contact.php", "/login.php", "/register.php",
    "/config.php", "/database.php", "/db.php",
    "/setup.php", "/install.php", "/upgrade.php",
    "/shell.php", "/webshell.php", "/cmd.php",

    # ── Misc ──────────────────────────────────────────────────────
    "/about", "/contact", "/help", "/faq", "/support",
    "/terms", "/privacy", "/legal",
    "/blog", "/news", "/press",
    "/feed", "/rss", "/atom",
    "/sitemap", "/changelog", "/readme",
    "/internal", "/private", "/secret",
    "/keys", "/key", "/secret", "/secrets",
    "/token", "/tokens", "/credential", "/credentials",
    "/certificate", "/cert",
    "/shell", "/cmd", "/exec", "/execute", "/run",
    "/install", "/setup", "/update", "/upgrade",
    "/cron", "/jobs", "/queue", "/tasks", "/worker",
    "/report", "/analytics", "/tracking",
    "/proxy", "/redirect", "/forward",
    "/cors", "/csp",
]

# ═══════════════════════════════════════════════════════════════════
#  UI HELPERS
# ═══════════════════════════════════════════════════════════════════

W  = Style.RESET_ALL
C  = Fore.CYAN
G  = Fore.GREEN
R  = Fore.RED
Y  = Fore.YELLOW
B  = Fore.BLUE
M  = Fore.MAGENTA
DG = Fore.LIGHTBLACK_EX


def banner():
    print(f"""
{C}╔══════════════════════════════════════════════════════════════════════════════╗
║{M}   ███████╗███╗   ██╗██████╗ ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗  {C}║
║{M}   ██╔════╝████╗  ██║██╔══██╗██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝  {C}║
║{M}   █████╗  ██╔██╗ ██║██║  ██║███████║██║   ██║██╔██╗ ██║   ██║   █████╗    {C}║
║{M}   ██╔══╝  ██║╚██╗██║██║  ██║██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝    {C}║
║{M}   ███████╗██║ ╚████║██████╔╝██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗  {C}║
║{M}   ╚══════╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝  {C}║
║                                                                                 ║
║{Y}              H U N T E R   U L T I M A T E   v 5 . 0   by @Burhan_ALDeen  {C}║
║{DG}           Full Params • Multi-Source • Smart Dedup • Organized           {C}║
╚═════════════════════════════════════════════════════════════════════════════════╝{W}
""")


def section(title: str, icon: str = "◈"):
    width = 78
    pad   = (width - len(title) - 4) // 2
    print(f"\n{C}╔{'═'*width}╗")
    print(f"║{' '*pad}{icon}  {Y}{title}{C}{' '*(width - pad - len(title) - 3)}║")
    print(f"╚{'═'*width}╝{W}")


def subsection(name: str):
    print(f"\n{B}  ┌─ {Y}{name}{W}")


def ok(msg):    print(f"{G}  ├─ ✓  {msg}{W}")
def fail(msg):  print(f"{R}  ├─ ✗  {msg}{W}")
def info(msg):  print(f"{Y}  ├─ ℹ  {msg}{W}")
def dot(msg):   print(f"{DG}  │     {msg}{W}")



# ═══════════════════════════════════════════════════════════════════
#  CORE CLASSES
# ═══════════════════════════════════════════════════════════════════

class Endpoint:
    def __init__(self, path: str, params: dict = None, full_url: str = "", source: str = ""):
        self.path     = path
        self.params   = params or {}
        self.full_url = full_url
        self.source   = source  # ✅ تتبع المصدر

    @property
    def full_path(self) -> str:
        if self.params:
            return f"{self.path}?{urlencode(self.params, doseq=True)}"
        return self.path

    @property
    def param_keys(self) -> list:
        return sorted(self.params.keys())

    def dedup_key(self) -> str:
        return f"{self.path}?{','.join(self.param_keys)}" if self.params else self.path

    def __repr__(self):
        return f"Endpoint({self.full_path})"


# ═══════════════════════════════════════════════════════════════════
#  UTILS
# ═══════════════════════════════════════════════════════════════════

def is_valid_path(path: str) -> bool:
    if not path or not path.startswith('/'):
        return False
    if path == '/':
        return False
    first_segment = path.lstrip('/').split('/')[0]
    if '.' in first_segment and not first_segment.startswith('.'):
        return False
    if len(path.rstrip('/')) < 2:
        return False
    return True


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


def parse_endpoint_from_url(raw_url: str, target_domain: str, source: str = "") -> Endpoint | None:
    if not raw_url:
        return None
    try:
        raw_url = raw_url.strip()
        if not is_subdomain_match(raw_url, target_domain):
            return None
        if '://' in raw_url:
            parsed = urlparse(raw_url)
        elif raw_url.startswith('//'):
            parsed = urlparse('https:' + raw_url)
        else:
            parsed = urlparse('https://' + target_domain + '/' + raw_url.lstrip('/'))

        path = parsed.path or '/'
        if len(path) > 1:
            path = path.rstrip('/')

        params = parse_qs(parsed.query, keep_blank_values=False)

        if path == '/' and not params:
            return None
        if path != '/' and not is_valid_path(path):
            return None

        return Endpoint(path=path, params=params, full_url=raw_url, source=source)
    except Exception:
        return None


def retry_request(func, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(0.3)
    return None


def deduplicate_endpoints(endpoints: list) -> list:
    seen = {}
    for ep in endpoints:
        key = ep.dedup_key()
        if key not in seen:
            seen[key] = ep
        else:
            if len(str(ep.params)) > len(str(seen[key].params)):
                seen[key] = ep
    return list(seen.values())


# ═══════════════════════════════════════════════════════════════════
#  LIVE CHECKER
# ═══════════════════════════════════════════════════════════════════

def check_endpoint_live(endpoint: Endpoint, domain: str, protocol: str = "https", result_queue=None) -> dict:
    result = {
        'path':      endpoint.path,
        'params':    endpoint.params,
        'full_path': endpoint.full_path,
        'source':    endpoint.source,
        'status':    'ERR',
        'length':    0,
        'title':     '',
        'redirect':  '',
    }
    try:
        url = f"{protocol}://{domain}{endpoint.full_path}"
        r   = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=TIMEOUT,
            verify=False,
            allow_redirects=True
        )
        result['status'] = r.status_code
        result['length'] = len(r.content)
        if r.history:
            result['redirect'] = r.url

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


# ═══════════════════════════════════════════════════════════════════
#  DATA SOURCES
# ═══════════════════════════════════════════════════════════════════

def fetch_wayback(domain: str) -> list:
    endpoints = []
    try:
        url = (
            f"https://web.archive.org/cdx/search/cdx"
            f"?url={domain}/*&output=json&fl=original&limit=5000"
            f"&filter=statuscode:200"
        )
        resp = retry_request(requests.get, url, timeout=40)
        if resp and resp.status_code == 200:
            data = resp.json()
            for item in data[1:]:
                raw_url = item[0] if isinstance(item, list) else item
                ep = parse_endpoint_from_url(raw_url, domain, source="Wayback Machine")
                if ep:
                    endpoints.append(ep)
    except Exception as e:
        fail(f"Wayback: {e}")
    return endpoints


def fetch_wayback_params(domain: str) -> list:
    endpoints = []
    try:
        url = (
            f"https://web.archive.org/cdx/search/cdx"
            f"?url={domain}/*%3F*&output=json&fl=original&limit=3000"
        )
        resp = retry_request(requests.get, url, timeout=40)
        if resp and resp.status_code == 200:
            data = resp.json()
            for item in data[1:]:
                raw_url = item[0] if isinstance(item, list) else item
                ep = parse_endpoint_from_url(raw_url, domain, source="Wayback Machine (params)")
                if ep and ep.params:
                    endpoints.append(ep)
    except Exception as e:
        fail(f"Wayback params: {e}")
    return endpoints


def fetch_otx(domain: str) -> list:
    endpoints = []
    if not OTX_API_KEY:
        return endpoints
    try:
        for page in range(1, 10):
            url     = f"https://otx.alienvault.com/api/v1/indicators/hostname/{domain}/url_list?limit=200&page={page}"
            headers = {"X-OTX-API-KEY": OTX_API_KEY}
            resp    = retry_request(requests.get, url, headers=headers, timeout=15)
            if not resp or resp.status_code != 200:
                break
            data  = resp.json()
            items = data.get('url_list', [])
            if not items:
                break
            for item in items:
                ep = parse_endpoint_from_url(item.get('url', ''), domain, source="AlienVault OTX")
                if ep:
                    endpoints.append(ep)
            time.sleep(0.3)
    except Exception:
        pass
    return endpoints


def fetch_vt(domain: str) -> list:
    endpoints = []
    for key in VT_API_KEYS:
        try:
            url     = f"https://www.virustotal.com/api/v3/domains/{domain}/urls?limit=40"
            headers = {"x-apikey": key}
            resp    = requests.get(url, headers=headers, timeout=15)
            if resp.status_code in [401, 403]:
                continue
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('data', []):
                    raw_url = item.get('attributes', {}).get('url', '')
                    if raw_url:
                        ep = parse_endpoint_from_url(raw_url, domain, source="VirusTotal")
                        if ep:
                            endpoints.append(ep)
                cursor = data.get('meta', {}).get('cursor')
                while cursor and len(endpoints) < 500:
                    nr = requests.get(
                        f"https://www.virustotal.com/api/v3/domains/{domain}/urls?limit=40&cursor={cursor}",
                        headers=headers, timeout=15
                    )
                    if nr.status_code != 200:
                        break
                    nd = nr.json()
                    for item in nd.get('data', []):
                        raw_url = item.get('attributes', {}).get('url', '')
                        if raw_url:
                            ep = parse_endpoint_from_url(raw_url, domain, source="VirusTotal")
                            if ep:
                                endpoints.append(ep)
                    cursor = nd.get('meta', {}).get('cursor')
                    time.sleep(0.5)
                if endpoints:
                    break
        except Exception:
            continue

    # VT v2 fallback
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
                                ep = parse_endpoint_from_url(raw_url, domain, source="VirusTotal (v2)")
                                if ep:
                                    endpoints.append(ep)
                        if endpoints:
                            break
            except Exception:
                continue
    return endpoints


def fetch_urlscan(domain: str) -> list:
    endpoints = []
    if not URLSCAN_API_KEY:
        return endpoints
    try:
        headers = {"API-Key": URLSCAN_API_KEY}
        url     = f"https://urlscan.io/api/v1/search/?q=page.domain:{domain}&size=200"
        resp    = retry_request(requests.get, url, headers=headers, timeout=20)
        if resp and resp.status_code == 200:
            data = resp.json()
            for result in data.get('results', []):
                raw_url = result.get('task', {}).get('url') or result.get('page', {}).get('url')
                if raw_url:
                    ep = parse_endpoint_from_url(raw_url, domain, source="URLScan.io")
                    if ep:
                        endpoints.append(ep)
    except Exception:
        pass
    return endpoints


def fetch_commoncrawl(domain: str) -> list:
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
                        ep      = parse_endpoint_from_url(raw_url, domain, source="CommonCrawl")
                        if ep:
                            endpoints.append(ep)
                    except:
                        continue
    except:
        pass
    return endpoints


def fetch_github_paths(domain: str) -> list:
    endpoints = []
    if not GITHUB_TOKEN:
        return endpoints
    try:
        headers      = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        query        = f'"{domain}" in:file'
        url          = f"https://api.github.com/search/code?q={query}&per_page=30"
        resp         = retry_request(requests.get, url, headers=headers, timeout=15)
        if not resp or resp.status_code != 200:
            return endpoints

        path_pattern = re.compile(r'(?:"|\'|`)(/[a-zA-Z0-9_\-/\.]+)(?:"|\'|`)')
        for item in resp.json().get('items', [])[:10]:
            try:
                file_resp = requests.get(item.get('url', ''), headers=headers, timeout=10)
                if file_resp.status_code != 200:
                    continue
                file_data = file_resp.json()
                content   = base64.b64decode(file_data.get('content', '')).decode('utf-8', errors='ignore')
                for match in path_pattern.findall(content):
                    if is_valid_path(match):
                        endpoints.append(Endpoint(path=match, source="GitHub"))
                time.sleep(0.5)
            except:
                continue
    except Exception:
        pass
    return endpoints


# ─── NEW SOURCES ───────────────────────────────────────────────────

def fetch_crtsh(domain: str) -> list:
    """
    crt.sh — subdomains → then we probe known paths on each subdomain.
    (here we just return paths, not full subdomain scanning)
    Actually we use crt.sh's URL index to find linked paths.
    """
    endpoints = []
    try:
        # crt.sh doesn't have a direct URL search, but we can find subdomains
        # then use them as seeds for wayback
        url  = f"https://crt.sh/?q=%.{domain}&output=json"
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            seen = set()
            for entry in data:
                name = entry.get('name_value', '')
                for sub in name.split('\n'):
                    sub = sub.strip().lstrip('*.')
                    if sub and sub not in seen and domain in sub:
                        seen.add(sub)
    except Exception:
        pass
    return endpoints


def fetch_hackertarget(domain: str) -> list:
    """HackerTarget — free URL crawler index"""
    endpoints = []
    try:
        url  = f"https://api.hackertarget.com/pagelinks/?q={domain}"
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200 and "API count exceeded" not in resp.text:
            for line in resp.text.splitlines():
                line = line.strip()
                if line and domain in line:
                    ep = parse_endpoint_from_url(line, domain, source="HackerTarget")
                    if ep:
                        endpoints.append(ep)
    except Exception:
        pass
    return endpoints


def fetch_rapiddns(domain: str) -> list:
    """RapidDNS — URL list from their crawl"""
    endpoints = []
    try:
        url  = f"https://rapiddns.io/subdomain/{domain}?full=1&down=1"
        resp = requests.get(url, timeout=15, headers={'User-Agent': USER_AGENT})
        if resp.status_code == 200:
            # extract any paths mentioned in the page
            paths = re.findall(r'href=["\']([^"\']+)["\']', resp.text)
            for p in paths:
                if p.startswith('/') and len(p) > 2:
                    if is_valid_path(p):
                        endpoints.append(Endpoint(path=p, source="RapidDNS"))
    except Exception:
        pass
    return endpoints


def fetch_openbugbounty(domain: str) -> list:
    """OpenBugBounty — sometimes lists publicly known endpoints"""
    endpoints = []
    try:
        url  = f"https://www.openbugbounty.org/api/1/search/?domain={domain}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for entry in data.get('results', []):
                raw_url = entry.get('url', '')
                if raw_url:
                    ep = parse_endpoint_from_url(raw_url, domain, source="OpenBugBounty")
                    if ep:
                        endpoints.append(ep)
    except Exception:
        pass
    return endpoints


def fetch_sitemap(domain: str) -> list:
    """Parse sitemap.xml directly"""
    endpoints = []
    for proto in ['https', 'http']:
        for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap.json']:
            try:
                url  = f"{proto}://{domain}{path}"
                resp = requests.get(url, timeout=10, headers={'User-Agent': USER_AGENT}, verify=False)
                if resp.status_code == 200 and '<url' in resp.text:
                    urls = re.findall(r'<loc>(.*?)</loc>', resp.text, re.IGNORECASE)
                    for raw_url in urls:
                        ep = parse_endpoint_from_url(raw_url.strip(), domain, source="Sitemap.xml")
                        if ep:
                            endpoints.append(ep)
                    if endpoints:
                        break
            except Exception:
                pass
        if endpoints:
            break
    return endpoints


def fetch_robots(domain: str) -> list:
    """Parse robots.txt for disallowed / allowed paths"""
    endpoints = []
    try:
        url  = f"https://{domain}/robots.txt"
        resp = requests.get(url, timeout=10, headers={'User-Agent': USER_AGENT}, verify=False)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                parts = line.strip().split(':', 1)
                if len(parts) == 2 and parts[0].strip().lower() in ('disallow', 'allow', 'sitemap'):
                    val = parts[1].strip()
                    if val.startswith('/'):
                        ep = Endpoint(path=val.split('?')[0], source="robots.txt")
                        if is_valid_path(ep.path):
                            endpoints.append(ep)
    except Exception:
        pass
    return endpoints


def fetch_jsfinder(domain: str) -> list:
    """Extract paths from JavaScript files served by the target"""
    endpoints = []
    try:
        # Get homepage first
        resp = requests.get(f"https://{domain}", timeout=10, headers={'User-Agent': USER_AGENT}, verify=False)
        if resp.status_code != 200:
            return endpoints

        # Find JS files
        js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', resp.text)
        path_re = re.compile(r'["\`\'](\/[a-zA-Z0-9_\-\/\.]+(?:\?[a-zA-Z0-9_\-=&%]+)?)["\`\']')

        for js_url in js_urls[:15]:  # limit
            try:
                if js_url.startswith('//'):
                    js_url = 'https:' + js_url
                elif js_url.startswith('/'):
                    js_url = f"https://{domain}{js_url}"
                elif not js_url.startswith('http'):
                    js_url = f"https://{domain}/{js_url}"

                if domain not in js_url and not js_url.startswith('/'):
                    continue

                jr = requests.get(js_url, timeout=10, headers={'User-Agent': USER_AGENT}, verify=False)
                if jr.status_code == 200:
                    for match in path_re.findall(jr.text):
                        ep = parse_endpoint_from_url(match if '://' in match else f"https://{domain}{match}",
                                                     domain, source="JS File")
                        if ep:
                            endpoints.append(ep)
            except:
                continue
    except Exception:
        pass
    return endpoints


# ═══════════════════════════════════════════════════════════════════
#  ACTIVE FUZZER  (improved)
# ═══════════════════════════════════════════════════════════════════

def active_fuzzer(domain: str) -> list:
    found    = []
    total    = len(COMMON_PATHS)
    checked  = [0]
    lock     = threading.Lock()
    rq       = queue.Queue()

    def display():
        while True:
            try:
                res = rq.get(timeout=0.1)
                if res is None:
                    break
                with lock:
                    found.append(res)
                    checked[0] += 1

                status = res['status']
                if status == 200:
                    color = G
                elif status in [301, 302, 307, 308]:
                    color = C
                elif status == 403:
                    color = Y
                elif status == 401:
                    color = M
                else:
                    color = DG

                length = res.get('length', 0)
                title  = f"  {DG}«{res['title'][:45]}»{W}" if res.get('title') else ""
                size   = f"  {DG}{length}b{W}" if length else ""
                ctr    = f"{DG}[{checked[0]}/{total}]{W}"
                print(f"  {ctr}  {color}[{status}]{W}  {res['full_path']}{size}{title}")

            except queue.Empty:
                continue

    t = threading.Thread(target=display, daemon=True)
    t.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
        futures = [
            ex.submit(check_endpoint_live, Endpoint(p, source="Active Fuzz"), domain, "https", rq)
            for p in COMMON_PATHS
        ]
        concurrent.futures.wait(futures)

    rq.put(None)
    t.join()
    return found


# ═══════════════════════════════════════════════════════════════════
#  OUTPUT  (organized per source + raw section)
# ═══════════════════════════════════════════════════════════════════

def status_color(status) -> str:
    if status == 200:
        return G
    elif status in [301, 302, 307, 308]:
        return C
    elif status == 403:
        return Y
    elif status == 401:
        return M
    elif status == 404:
        return DG
    return W


def save_results(all_results: list, domain: str, source_map: dict = None):
    """
    ✅ Saves organized output:
    - Section per source (with per-source endpoints)
    - Final RAW section (all unique full_paths, one per line)
    """
    valid = [r for r in all_results if isinstance(r.get('status'), int)]

    # ── Group by source ─────────────────────────────────────────────
    by_source = defaultdict(list)
    for r in valid:
        src = r.get('source', 'Unknown')
        by_source[src].append(r)

    # ── Unique full_paths for RAW section ───────────────────────────
    all_paths = sorted(set(r['full_path'] for r in valid))

    sep = "=" * 80

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"EndpointsHunter v5.0  —  {domain}\n")
        f.write(f"Scan Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Live : {len(valid)}\n")
        f.write(f"Unique     : {len(all_paths)}\n")
        f.write(f"{sep}\n\n")

        # ── Per-source sections ──────────────────────────────────────
        for src, items in sorted(by_source.items()):
            f.write(f"\n{'─'*80}\n")
            f.write(f"  SOURCE: {src}  ({len(items)} endpoints)\n")
            f.write(f"{'─'*80}\n")

            for r in sorted(items, key=lambda x: x['full_path']):
                status   = r['status']
                length   = r.get('length', 0)
                title    = r.get('title', '')
                params   = r.get('params', {})
                redirect = r.get('redirect', '')

                f.write(f"  [{status}]  {r['full_path']}")
                if length:
                    f.write(f"  [{length}b]")
                if title:
                    f.write(f"  «{title}»")
                if params:
                    param_str = ", ".join(f"{k}={v[0] if v else ''}" for k, v in params.items())
                    f.write(f"\n         PARAMS: {param_str}")
                if redirect:
                    f.write(f"\n         REDIRECT → {redirect}")
                f.write("\n")

        # ── RAW section ──────────────────────────────────────────────
        f.write(f"\n\n{sep}\n")
        f.write(f"  RAW — ALL UNIQUE ENDPOINTS  ({len(all_paths)} total)\n")
        f.write(f"  (Copy-paste ready for fuzzing tools)\n")
        f.write(f"{sep}\n\n")

        for p in all_paths:
            f.write(f"{p}\n")

        # ── Parameters summary ───────────────────────────────────────
        params_list = [(r['full_path'], list(r['params'].keys()))
                       for r in valid if r.get('params')]
        if params_list:
            f.write(f"\n\n{sep}\n")
            f.write(f"  ENDPOINTS WITH PARAMETERS  ({len(params_list)})\n")
            f.write(f"{sep}\n\n")
            for fp, keys in params_list:
                f.write(f"  {fp}\n")
                f.write(f"    ↳ params: {', '.join(keys)}\n")

    print(f"\n{G}  ✓ Saved {len(all_paths)} unique endpoints → {OUTPUT_FILE}{W}")

    # ── JSON output ──────────────────────────────────────────────────
    json_data = {
        'domain':      domain,
        'scan_time':   datetime.now().isoformat(),
        'total_live':  len(valid),
        'unique':      len(all_paths),
        'by_source':   {src: len(items) for src, items in by_source.items()},
        'endpoints':   valid,
    }
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)

    print(f"{G}  ✓ Detailed JSON   → {JSON_OUTPUT}{W}")


# ═══════════════════════════════════════════════════════════════════
#  SUBDOMAIN LIST MODE
# ═══════════════════════════════════════════════════════════════════

def fmt_size(b: int) -> str:
    if b >= 1_048_576:
        return f"{b/1_048_576:.1f}MB"
    elif b >= 1024:
        return f"{b/1024:.1f}KB"
    return f"{b}B"


def is_wildcard_200(domain: str, sample_paths: int = 3) -> tuple[bool, set]:
    """
    يفحص إذا كان السيرفر يرد 200 على أي شي (wildcard).
    يطلب مسارات عشوائية — لو كلها 200 بنفس الحجم تقريباً = wildcard.
    يرجع (is_wildcard, baseline_sizes)
    """
    import random, string
    test_paths = [
        '/' + ''.join(random.choices(string.ascii_lowercase, k=12))
        for _ in range(sample_paths)
    ]
    sizes = []
    for p in test_paths:
        try:
            r = requests.get(
                f"https://{domain}{p}",
                headers={'User-Agent': USER_AGENT},
                timeout=TIMEOUT, verify=False, allow_redirects=True
            )
            if r.status_code == 200:
                sizes.append(len(r.content))
        except:
            pass

    if len(sizes) < sample_paths:
        return False, set()

    # لو كل الردود 200 والأحجام متقاربة جداً (فرق < 5%) = wildcard
    avg  = sum(sizes) / len(sizes)
    diffs = [abs(s - avg) / avg for s in sizes]
    if all(d < 0.05 for d in diffs):
        return True, set(sizes)

    return False, set()


def fuzz_subdomain(subdomain: str, paths: list, wildcard_sizes: set, is_wildcard: bool) -> list:
    """
    يفحص مسارات الـ wordlist على subdomain معين.
    في حالة wildcard: يعرض فقط 200 التي حجمها مختلف عن baseline.
    يزيل التكرار: نفس المسار بنفس الحجم = تكرار.
    """
    found      = []
    seen_sizes = set(wildcard_sizes)  # نسخة للـ subdomain الحالي

    def check(path):
        try:
            r = requests.get(
                f"https://{subdomain}{path}",
                headers={'User-Agent': USER_AGENT},
                timeout=TIMEOUT, verify=False, allow_redirects=True
            )
            size = len(r.content)

            if r.status_code != 200:
                return None

            # wildcard check: تجاهل لو الحجم موجود في baseline
            if is_wildcard and size in seen_sizes:
                return None

            # dedup: نفس المسار بنفس الحجم مرة ثانية = تجاهل
            key = f"{path}:{size}"
            if key in seen_sizes:
                return None
            seen_sizes.add(key)

            title = ""
            m = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
            if m:
                title = m.group(1).strip()[:60]

            return {
                'path':   path,
                'status': 200,
                'size':   size,
                'title':  title,
            }
        except:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        for result in ex.map(check, paths):
            if result:
                found.append(result)

    return found


def run_subdomain_list_mode(sub_file: str, wordlist: list):
    """
    المود الكامل لفحص قائمة subdomains
    """
    # قراءة الملف
    try:
        with open(sub_file, 'r', encoding='utf-8') as f:
            raw_lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"\n  {R}✗ File not found: {sub_file}{W}")
        sys.exit(1)

    # تنظيف
    subdomains = []
    for line in raw_lines:
        line = line.replace('http://', '').replace('https://', '').split('/')[0]
        if line:
            subdomains.append(line)

    subdomains = list(dict.fromkeys(subdomains))  # remove dups

    section(f"SUBDOMAIN LIST MODE  —  {len(subdomains)} targets", "◈")
    info(f"Wordlist: {len(wordlist)} paths")
    info(f"Output will show 200-only, smart dedup enabled\n")

    all_findings  = {}   # subdomain → [results]
    output_lines  = []   # للملف النهائي

    for idx, sub in enumerate(subdomains, 1):
        prefix = f"{DG}[{idx}/{len(subdomains)}]{W}"
        print(f"\n  {prefix}  {C}{sub}{W}")

        # wildcard detection
        is_wc, wc_sizes = is_wildcard_200(sub)
        if is_wc:
            print(f"    {Y}⚠  Wildcard 200 detected — filtering by response size{W}")
        else:
            print(f"    {G}✓  No wildcard{W}")

        # fuzz
        results = fuzz_subdomain(sub, wordlist, wc_sizes, is_wc)

        if not results:
            print(f"    {DG}─  No interesting 200s found{W}")
            continue

        all_findings[sub] = results
        print(f"    {G}◉  {len(results)} unique endpoint(s) found:{W}")
        for r in sorted(results, key=lambda x: x['path']):
            size_str  = fmt_size(r['size'])
            title_str = f"  {DG}«{r['title']}»{W}" if r['title'] else ""
            print(f"      {G}[200]{W}  {r['path']}  {Y}{size_str}{W}{title_str}")
            output_lines.append(f"https://{sub}{r['path']}")

    # ── حفظ النتائج ─────────────────────────────────────────────────
    section("SAVING RESULTS", "💾")

    out_file  = "subdomains_endpoints.txt"
    json_file = "subdomains_endpoints.json"

    sep = "=" * 80
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"EndpointsHunter v5.0  —  Subdomain List Mode\n")
        f.write(f"Scan Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Targets   : {len(subdomains)}\n")
        f.write(f"Found     : {sum(len(v) for v in all_findings.values())} endpoints across {len(all_findings)} subdomains\n")
        f.write(f"{sep}\n\n")

        for sub, results in sorted(all_findings.items()):
            f.write(f"\n{'─'*80}\n")
            f.write(f"  {sub}  ({len(results)} endpoints)\n")
            f.write(f"{'─'*80}\n")
            for r in sorted(results, key=lambda x: x['path']):
                title_str = f"  «{r['title']}»" if r['title'] else ""
                f.write(f"  [200]  {r['path']}  [{fmt_size(r['size'])}]{title_str}\n")

        f.write(f"\n\n{sep}\n")
        f.write(f"  RAW — ALL UNIQUE ENDPOINTS\n")
        f.write(f"{sep}\n\n")
        for line in sorted(set(output_lines)):
            f.write(f"{line}\n")

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'scan_time': datetime.now().isoformat(),
            'targets':   len(subdomains),
            'findings':  {sub: res for sub, res in all_findings.items()},
        }, f, indent=2)

    total = sum(len(v) for v in all_findings.values())
    print(f"\n  {G}✓ {total} endpoints across {len(all_findings)} subdomains{W}")
    print(f"  {G}✓ Saved → {out_file}{W}")
    print(f"  {G}✓ JSON  → {json_file}{W}")
    section("SCAN COMPLETE", "✓")


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    banner()

    # ── Mode selection ────────────────────────────────────────────────
    print(f"  {C}Select mode:{W}")
    print(f"  {Y}[1]{W}  Single domain scan  (passive harvest + live check)")
    print(f"  {Y}[2]{W}  Subdomain list mode  (wordlist fuzz on each sub)\n")

    mode = input(f"{C}  ◈  Mode [1/2]: {W}").strip()

    if mode == "2":
        sub_file = input(f"{C}  ◈  Path to subdomain list (e.g. sub.txt): {W}").strip()
        print(f"\n  {C}Wordlist:{W}")
        print(f"  {Y}[1]{W}  Built-in ({len(COMMON_PATHS)} paths)")
        print(f"  {Y}[2]{W}  Custom wordlist file")
        wl_choice = input(f"{C}  ◈  Choice [1/2]: {W}").strip()

        if wl_choice == "2":
            wl_file = input(f"{C}  ◈  Wordlist file path: {W}").strip()
            try:
                with open(wl_file, 'r', encoding='utf-8') as f:
                    wordlist = [l.strip() for l in f if l.strip() and l.strip().startswith('/')]
                info(f"Loaded {len(wordlist)} paths from {wl_file}")
            except FileNotFoundError:
                fail(f"File not found: {wl_file} — using built-in")
                wordlist = COMMON_PATHS
        else:
            wordlist = COMMON_PATHS

        run_subdomain_list_mode(sub_file, wordlist)
        return

    # ── Single domain mode ────────────────────────────────────────────
    domain = input(f"{C}  ◈  Enter target domain: {W}").strip()
    if not domain:
        sys.exit(1)
    domain = domain.replace('http://', '').replace('https://', '').split('/')[0]

    print(f"\n  {Y}Target → {W}{domain}\n")

    # ── Step 1: Passive Harvesting ───────────────────────────────────
    section("STEP 1 — PASSIVE HARVESTING", "◈")

    collectors = [
        (fetch_wayback,       "Wayback Machine"),
        (fetch_wayback_params,"Wayback Machine (params)"),
        (fetch_commoncrawl,   "CommonCrawl"),
        (fetch_otx,           "AlienVault OTX"),
        (fetch_vt,            "VirusTotal"),
        (fetch_urlscan,       "URLScan.io"),
        (fetch_github_paths,  "GitHub"),
        (fetch_hackertarget,  "HackerTarget"),
        (fetch_sitemap,       "Sitemap.xml"),
        (fetch_robots,        "robots.txt"),
        (fetch_jsfinder,      "JS File Mining"),
        (fetch_openbugbounty, "OpenBugBounty"),
    ]

    all_raw: list[Endpoint] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        future_map = {executor.submit(func, domain): name for func, name in collectors}
        for future in concurrent.futures.as_completed(future_map):
            source = future_map[future]
            try:
                eps   = future.result()
                count = len(eps)
                all_raw.extend(eps)
                if count > 0:
                    ok(f"{source:<32}  {G}{count:>4} endpoints{W}")
                else:
                    dot(f"{source:<32}  {DG}   0 endpoints{W}")
            except Exception as e:
                fail(f"{source}: {e}")

    # ── Dedup ─────────────────────────────────────────────────────────
    deduped     = deduplicate_endpoints(all_raw)
    with_params = [ep for ep in deduped if ep.params]
    no_params   = [ep for ep in deduped if not ep.params]

    print(f"\n  {C}Total unique endpoints : {G}{len(deduped)}{W}")
    print(f"  {C}  ├─ With parameters   : {Y}{len(with_params)}{W}")
    print(f"  {C}  └─ Without parameters: {W}{len(no_params)}{W}")

    # ── Step 2: Live Checking ─────────────────────────────────────────
    section("STEP 2 — LIVE ENDPOINT CHECKING", "◉")

    if not deduped:
        print(f"\n  {R}No passive endpoints found. Jumping to active fuzzing...{W}")
        fuzzed = active_fuzzer(domain)
        if fuzzed:
            save_results(fuzzed, domain)
        else:
            print(f"  {R}Nothing found.{W}")
        section("SCAN COMPLETE", "✓")
        return

    # Prioritize
    priority_kw  = ['/api', '/graphql', '/admin', '/login', '/auth', '/config',
                    '/swagger', '/v1', '/v2', '/token', '/user', '/upload']
    priority_eps = [ep for ep in deduped if any(kw in ep.path.lower() for kw in priority_kw)]
    other_eps    = [ep for ep in deduped if ep not in priority_eps]

    if len(deduped) > MAX_ENDPOINTS_TO_CHECK:
        info(f"Checking {MAX_ENDPOINTS_TO_CHECK} prioritized out of {len(deduped)}")
        endpoints_to_check = priority_eps[:400] + other_eps[:MAX_ENDPOINTS_TO_CHECK - 400]
    else:
        info(f"Checking all {len(deduped)} endpoints")
        endpoints_to_check = deduped

    valid_results = []
    rq            = queue.Queue()
    checked_n     = [0]
    lock          = threading.Lock()

    def display_live():
        while True:
            try:
                res = rq.get(timeout=0.1)
                if res is None:
                    break
                with lock:
                    valid_results.append(res)
                    checked_n[0] += 1
                    n = checked_n[0]

                status = res['status']
                color  = status_color(status)
                length = res.get('length', 0)
                title  = f"  {DG}«{res['title'][:40]}»{W}" if res.get('title') else ""
                params = f"  {Y}❬{' '.join(res['params'].keys())}❭{W}" if res.get('params') else ""
                size   = f"  {DG}{length}b{W}" if length else ""
                ctr    = f"{DG}[{n}/{len(endpoints_to_check)}]{W}"

                print(f"  {ctr}  {color}[{status}]{W}  {res['full_path']}{size}{params}{title}")

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

    print(f"\n\n  {G}✓ Live check complete — {len(valid_results)} endpoints responded{W}")

    # ── Also fuzz if few results ──────────────────────────────────────
    if len(valid_results) < 10:
        section("STEP 2b — ACTIVE FUZZING (supplemental)", "⚡")
        info(f"Running wordlist ({len(COMMON_PATHS)} paths) to supplement...")
        fuzz_results = active_fuzzer(domain)
        valid_results.extend(fuzz_results)

    # ── Save ──────────────────────────────────────────────────────────
    section("STEP 3 — SAVING RESULTS", "💾")
    if valid_results:
        save_results(valid_results, domain)

        # Status summary
        status_counts = defaultdict(int)
        for r in valid_results:
            status_counts[r['status']] += 1

        print(f"\n  {C}Status Code Summary:{W}")
        for status in sorted(status_counts):
            count = status_counts[status]
            color = status_color(status)
            bar   = f"{color}{'█' * min(count, 50)}{W}"
            print(f"    {color}[{status}]{W}  {bar}  {Y}{count}{W}")

        # Params summary
        params_eps = [r for r in valid_results if r.get('params')]
        if params_eps:
            print(f"\n  {C}Endpoints with Parameters ({len(params_eps)}):{W}")
            for r in params_eps[:15]:
                keys = ', '.join(r['params'].keys())
                print(f"    {Y}{r['full_path']}{W}")
                print(f"      {DG}↳ {keys}{W}")
            if len(params_eps) > 15:
                print(f"    {DG}... and {len(params_eps)-15} more (see {JSON_OUTPUT}){W}")
    else:
        print(f"  {R}No live endpoints found.{W}")

    section(f"SCAN COMPLETE  —  {domain}", "✓")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{R}  [!] Interrupted by user{W}")
        sys.exit(0)
