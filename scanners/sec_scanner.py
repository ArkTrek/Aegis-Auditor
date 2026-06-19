import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import socket
import ssl
import datetime
from concurrent.futures import ThreadPoolExecutor

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

SPAM_KEYWORDS = [
    'viagra', 'cialis', 'levitra', 'xenical', 'tramadol', 'valium',
    'phentermine', 'casino', 'poker', 'betting', 'slot machine',
    'cheap pills', 'buy replica'
]

SENSITIVE_PATHS = [
    '/.env',
    '/.git/config',
    '/wp-config.php',
    '/composer.json',
    '/package.json',
    '/wp-admin/'
]

def check_tls_and_ssl(hostname):
    if not hostname:
        return {"valid": False, "error": "Invalid URL hostname"}, None
    
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    port = 443
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=4) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                tls_version = ssock.version()
                cipher = ssock.cipher()[0]
                
                if not cert:
                    return {"valid": False, "error": "No SSL certificate found"}, tls_version
                
                not_after_str = cert.get('notAfter')
                days_left = -1
                expiry_date = "Unknown"
                if not_after_str:
                    try:
                        expiry = datetime.datetime.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
                        days_left = (expiry - datetime.datetime.utcnow()).days
                        expiry_date = expiry.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass
                
                issuer_dict = dict(x[0] for x in cert.get('issuer', []))
                subject_dict = dict(x[0] for x in cert.get('subject', []))
                
                ssl_details = {
                    "valid": True,
                    "issuer": issuer_dict.get('commonName', 'Unknown'),
                    "subject": subject_dict.get('commonName', 'Unknown'),
                    "expiry": expiry_date,
                    "days_left": days_left,
                    "version": tls_version,
                    "cipher": cipher
                }
                return ssl_details, tls_version
    except Exception as e:
        return {"valid": False, "error": str(e)}, None

def check_sensitive_path(base_url, path):
    full_url = urljoin(base_url, path)
    try:
        res = requests.get(full_url, headers=HEADERS, timeout=3, allow_redirects=False)
        if res.status_code == 200:
            content_len = len(res.text.strip())
            if content_len > 15:
                return path, True, res.status_code
        return path, False, res.status_code
    except Exception:
        return path, False, 0

def check_waf(headers):
    waf_detected = "None Detected"
    waf_reasons = []
    
    server = headers.get('Server', '').lower()
    if 'cloudflare' in server or headers.get('CF-RAY') or headers.get('cf-cache-status'):
        waf_detected = "Cloudflare WAF"
        waf_reasons.append("Cloudflare headers found (Server/CF-RAY)")
    elif 'cloudfront' in server or headers.get('X-Amz-Cf-Id'):
        waf_detected = "AWS CloudFront / WAF"
        waf_reasons.append("Amazon CloudFront headers found")
    elif 'akamai' in server or headers.get('X-Akamai-Transformed') or 'akamaighost' in server:
        waf_detected = "Akamai WAF"
        waf_reasons.append("Akamai headers found")
    elif 'sucuri' in server or headers.get('x-sucuri-id') or headers.get('x-sucuri-cache'):
        waf_detected = "Sucuri WAF"
        waf_reasons.append("Sucuri header signatures found")
    elif 'fastly' in server or headers.get('X-Fastly-Request-ID'):
        waf_detected = "Fastly WAF"
        waf_reasons.append("Fastly header signatures found")
    elif headers.get('X-Barracuda-WAF'):
        waf_detected = "Barracuda WAF"
        waf_reasons.append("Barracuda WAF header found")
    elif headers.get('X-F5-Auth-Result') or 'bigip' in server:
        waf_detected = "F5 BIG-IP WAF"
        waf_reasons.append("F5 BIG-IP headers found")
        
    return {"name": waf_detected, "reasons": waf_reasons}

def analyze_security(url):
    if not url.startswith('http'):
        url = 'https://' + url

    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    report = {
        'target_url': url,
        'https_active': url.startswith('https'),
        'https_enforced': False,
        'ssl_details': None,
        'tls_version': None,
        'tls_issues': [],
        'headers_found': {
            'Strict-Transport-Security': False,
            'Content-Security-Policy': False,
            'X-Frame-Options': False,
            'X-Content-Type-Options': False,
            'Referrer-Policy': False,
            'Permissions-Policy': False,
            'X-XSS-Protection': False
        },
        'header_values': {
            'Strict-Transport-Security': None,
            'Content-Security-Policy': None,
            'X-Frame-Options': None,
            'X-Content-Type-Options': None,
            'Referrer-Policy': None,
            'Permissions-Policy': None,
            'X-XSS-Protection': None
        },
        'cookies': [],
        'waf': None,
        'cms_detected': None,
        'server_info': {
            'server_header': None,
            'powered_by_header': None,
            'disclosed': False
        },
        'exposed_files': [],
        'spam_keywords': [],
        'issues': [],
        'security_score': 100
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        server_headers = response.headers

        report['waf'] = check_waf(server_headers)

        if report['https_active']:
            http_url = url.replace('https://', 'http://')
            try:
                http_res = requests.get(http_url, headers=HEADERS, timeout=3, allow_redirects=False)
                if http_res.status_code in [301, 302, 307, 308] and 'https://' in http_res.headers.get('Location', ''):
                    report['https_enforced'] = True
            except Exception:
                report['https_enforced'] = True
        
        if report['https_active'] and hostname:
            ssl_details, tls_ver = check_tls_and_ssl(hostname)
            report['ssl_details'] = ssl_details
            report['tls_version'] = tls_ver
            if tls_ver and tls_ver in ['TLSv1', 'TLSv1.1', 'SSLv2', 'SSLv3']:
                report['tls_issues'].append(f'Outdated TLS version ({tls_ver}) is enabled. Disable TLS versions below 1.2.')
        else:
            report['ssl_details'] = {"valid": False, "error": "URL is HTTP-only"}

        for header in report['headers_found'].keys():
            matching_key = next((k for k in server_headers.keys() if k.lower() == header.lower()), None)
            if matching_key:
                report['headers_found'][header] = True
                report['header_values'][header] = server_headers[matching_key]

        server_header = server_headers.get('Server')
        powered_header = server_headers.get('X-Powered-By')
        report['server_info']['server_header'] = server_header
        report['server_info']['powered_by_header'] = powered_header
        if server_header or powered_header:
            report['server_info']['disclosed'] = True

        cookies_report = []
        for cookie in response.cookies:
            c_info = {
                'name': cookie.name,
                'secure': cookie.secure,
                'httponly': False,
                'samesite': None
            }
            if hasattr(cookie, 'has_nonstandard_attr') and cookie.has_nonstandard_attr('HttpOnly'):
                c_info['httponly'] = True
            elif '_rest' in cookie.__dict__ and any(k.lower() == 'httponly' for k in cookie._rest.keys()):
                c_info['httponly'] = True
                
            if '_rest' in cookie.__dict__:
                for k, v in cookie._rest.items():
                    if k.lower() == 'samesite':
                        c_info['samesite'] = v
                        break
            cookies_report.append(c_info)
        report['cookies'] = cookies_report

        body_text = soup.get_text().lower()
        for kw in SPAM_KEYWORDS:
            if kw in body_text:
                report['spam_keywords'].append(kw)

        meta_gen = soup.find('meta', attrs={'name': 'generator'})
        html_str = response.text.lower()
        if meta_gen and meta_gen.get('content') and 'wordpress' in meta_gen['content'].lower():
            report['cms_detected'] = 'WordPress'
        elif 'wp-content' in html_str or 'wp-includes' in html_str:
            report['cms_detected'] = 'WordPress'
        elif 'joomla!' in html_str or 'media/system/js' in html_str:
            report['cms_detected'] = 'Joomla'
        elif 'drupal.org' in html_str or 'sites/default/files' in html_str:
            report['cms_detected'] = 'Drupal'

        with ThreadPoolExecutor(max_workers=6) as executor:
            path_results = list(executor.map(lambda p: check_sensitive_path(base_url, p), SENSITIVE_PATHS))

        for path, exposed, code in path_results:
            if exposed:
                report['exposed_files'].append({
                    "file": path,
                    "url": urljoin(base_url, path),
                    "description": f"Exposed CMS or system path returns HTTP {code}.",
                    "status": "Exposed"
                })

        score = 0
        if report['https_active']:
            score += 20
        if report['ssl_details'] and report['ssl_details'].get('valid'):
            score += 20
        if report['headers_found']['Strict-Transport-Security']:
            score += 15
        if report['headers_found']['Content-Security-Policy']:
            score += 15
        if report['headers_found']['X-Frame-Options']:
            score += 10
        if report['headers_found']['X-Content-Type-Options']:
            score += 10
        if report['headers_found']['Referrer-Policy']:
            score += 5
        if report['headers_found']['Permissions-Policy']:
            score += 5

        if not report['https_enforced'] and report['https_active']:
            score -= 10
        if report['tls_issues']:
            score -= 15
        if report['server_info']['disclosed']:
            score -= 5
        if report['spam_keywords']:
            score -= 25
            
        cookie_penalty = 0
        for cookie in report['cookies']:
            if not cookie['secure'] or not cookie['httponly']:
                cookie_penalty += 5
        score -= min(10, cookie_penalty)

        if report['exposed_files']:
            score -= (25 * len(report['exposed_files']))

        report['security_score'] = max(0, min(100, score))
        return report

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to reach the site: {str(e)}"}