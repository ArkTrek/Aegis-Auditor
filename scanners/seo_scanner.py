import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import subprocess
import os
import time

def find_chrome():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def fetch_html_with_chrome(url):
    chrome_path = find_chrome()
    if not chrome_path:
        return None, "Google Chrome executable not found."
    
    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--dump-dom",
        "--no-sandbox",
        url
    ]
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=12, encoding='utf-8', errors='ignore')
        elapsed_time = round(time.time() - start_time, 3)
        if result.returncode == 0:
            return result.stdout, elapsed_time
        else:
            return None, f"Chrome error: exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return None, "Chrome request timed out"
    except Exception as e:
        return None, str(e)

def check_file_exists(base_url, path):
    url = urljoin(base_url, path)
    try:
        # Use HEAD request for speed, fall back to GET if HEAD is not allowed
        res = requests.head(url, timeout=3, allow_redirects=True)
        if res.status_code == 405:
            res = requests.get(url, timeout=3, allow_redirects=True)
        return res.status_code == 200, url
    except Exception:
        return False, url

def check_robots_txt(base_url):
    url = urljoin(base_url, '/robots.txt')
    try:
        res = requests.get(url, timeout=5, allow_redirects=True)
        if res.status_code == 200:
            content = res.text
            lines = content.splitlines()
            sitemaps = [line.split(':', 1)[1].strip() for line in lines if line.lower().startswith('sitemap:')]
            disallows = [line.split(':', 1)[1].strip() for line in lines if line.lower().startswith('disallow:')]
            return {
                'exists': True,
                'url': url,
                'content_preview': '\n'.join(lines[:10]) + ('\n...' if len(lines) > 10 else ''),
                'sitemaps_declared': sitemaps,
                'disallow_count': len(disallows)
            }
        return {'exists': False, 'url': url, 'content_preview': None, 'sitemaps_declared': [], 'disallow_count': 0}
    except Exception:
        return {'exists': False, 'url': url, 'content_preview': None, 'sitemaps_declared': [], 'disallow_count': 0}

def check_sitemap_xml(base_url):
    url = urljoin(base_url, '/sitemap.xml')
    try:
        res = requests.get(url, timeout=5, allow_redirects=True)
        if res.status_code == 200:
            content = res.text
            urls = re.findall(r'<loc>(.*?)</loc>', content)
            is_index = '<sitemap>' in content
            return {
                'exists': True,
                'url': url,
                'url_count': len(urls),
                'is_index': is_index,
                'type': 'Sitemap Index' if is_index else 'XML Sitemap'
            }
        return {'exists': False, 'url': url, 'url_count': 0, 'is_index': False, 'type': None}
    except Exception:
        return {'exists': False, 'url': url, 'url_count': 0, 'is_index': False, 'type': None}

def analyze_seo(url):
    if not url.startswith('http'):
        url = 'https://' + url

    report = {
        'target_url': url,
        'title': {
            'value': None,
            'length': 0,
            'status': 'Missing',
            'message': 'No title tag found'
        },
        'meta_description': {
            'value': None,
            'length': 0,
            'status': 'Missing',
            'message': 'No meta description tag found'
        },
        'canonical': {
            'value': None,
            'matches': False,
            'status': 'Missing'
        },
        'viewport_exists': False,
        'index_status': {
            'noindex': False,
            'reasons': []
        },
        'headings': {
            'h1': [],
            'h2': [],
            'h3': [],
            'counts': {
                'h1': 0, 'h2': 0, 'h3': 0, 'h4': 0, 'h5': 0, 'h6': 0
            }
        },
        'images': {
            'total': 0,
            'missing_alt': 0,
            'missing_alt_list': [],
            'modern_format_count': 0,
            'list': []
        },
        'links': {
            'total': 0,
            'internal_count': 0,
            'external_count': 0,
            'list': []
        },
        'social_metadata': {
            'og_title': None,
            'og_description': None,
            'og_image': None,
            'og_url': None,
            'og_type': None,
            'twitter_card': None,
            'twitter_title': None,
            'twitter_description': None,
            'twitter_image': None,
            'has_social': False
        },
        'files': {
            'robots_exists': False,
            'robots_url': None,
            'robots_details': None,
            'sitemap_exists': False,
            'sitemap_url': None,
            'sitemap_details': None
        },
        'performance_metrics': {
            'response_time_seconds': 0.0,
            'page_size_kb': 0.0,
            'word_count': 0,
            'reading_time_minutes': 0
        },
        'keyword_density': [],
        'seo_score': 100
    }

    try:
        html_content = None
        chrome_error = None
        response = None
        
        # Try fetching with Google Chrome first
        html_content, chrome_elapsed = fetch_html_with_chrome(url)
        if html_content and "<html" in html_content.lower():
            report['performance_metrics']['response_time_seconds'] = chrome_elapsed
            report['performance_metrics']['page_size_kb'] = round(len(html_content.encode('utf-8', errors='ignore')) / 1024.0, 2)
        else:
            chrome_error = chrome_elapsed or "Chrome returned empty DOM or non-HTML page"
            # Fallback to requests on timeout or failure
            response = requests.get(url, timeout=10)
            html_content = response.text
            report['performance_metrics']['response_time_seconds'] = round(response.elapsed.total_seconds(), 3)
            report['performance_metrics']['page_size_kb'] = round(len(response.content) / 1024.0, 2)

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Parse Title
        if soup.title and soup.title.string:
            title_text = soup.title.string.strip()
            report['title']['value'] = title_text
            report['title']['length'] = len(title_text)
            if len(title_text) > 60:
                report['title']['status'] = 'Warning'
                report['title']['message'] = 'Title is too long (over 60 characters)'
            else:
                report['title']['status'] = 'Good'
                report['title']['message'] = 'Title is optimized'

        # 2. Parse Meta Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc_text = meta_desc['content'].strip()
            report['meta_description']['value'] = desc_text
            report['meta_description']['length'] = len(desc_text)
            if len(desc_text) > 160:
                report['meta_description']['status'] = 'Warning'
                report['meta_description']['message'] = 'Meta description is too long (over 160 characters)'
            elif len(desc_text) < 50:
                report['meta_description']['status'] = 'Warning'
                report['meta_description']['message'] = 'Meta description is too short (under 50 characters)'
            else:
                report['meta_description']['status'] = 'Good'
                report['meta_description']['message'] = 'Meta description is optimized'

        # 3. Canonical Tag
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag and canonical_tag.get('href'):
            c_url = canonical_tag['href'].strip()
            report['canonical']['value'] = c_url
            report['canonical']['status'] = 'Good'
            parsed_target = urlparse(url)
            parsed_canonical = urlparse(c_url)
            if parsed_target.netloc == parsed_canonical.netloc and parsed_target.path == parsed_canonical.path:
                report['canonical']['matches'] = True

        # 4. Viewport Tag
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        if viewport_tag:
            report['viewport_exists'] = True

        # 5. Index Status
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        if meta_robots and meta_robots.get('content'):
            robots_content = meta_robots['content'].lower()
            if 'noindex' in robots_content:
                report['index_status']['noindex'] = True
                report['index_status']['reasons'].append("Meta robots noindex tag found")
        
        x_robots = response.headers.get('X-Robots-Tag', '').lower() if response else ''
        if 'noindex' in x_robots:
            report['index_status']['noindex'] = True
            report['index_status']['reasons'].append("X-Robots-Tag: noindex header found")

        # 6. Heading Hierarchy
        for h_level in range(1, 7):
            tags = soup.find_all(f'h{h_level}')
            report['headings']['counts'][f'h{h_level}'] = len(tags)
            for tag in tags:
                text = tag.get_text(strip=True)
                if text and h_level <= 3:
                    report['headings'][f'h{h_level}'].append(text)

        # 7. Images Audit
        images = soup.find_all('img')
        report['images']['total'] = len(images)
        for img in images:
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            is_modern = any(src.lower().endswith(ext) for ext in ['.webp', '.avif'])
            if is_modern:
                report['images']['modern_format_count'] += 1

            has_alt = alt is not None and alt.strip() != ''
            if not has_alt:
                report['images']['missing_alt'] += 1
                if len(report['images']['missing_alt_list']) < 10:
                    report['images']['missing_alt_list'].append(src)
            
            if len(report['images']['list']) < 30:
                report['images']['list'].append({
                    'src': src,
                    'alt': alt if alt is not None else '',
                    'has_alt': has_alt,
                    'is_modern': is_modern
                })

        # 8. Links Analysis
        parsed_base = urlparse(url)
        base_domain = parsed_base.netloc
        links = soup.find_all('a', href=True)
        report['links']['total'] = len(links)
        for link in links:
            href = link['href'].strip()
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            full_href = urljoin(url, href)
            parsed_href = urlparse(full_href)
            
            is_internal = (parsed_href.netloc == base_domain or not parsed_href.netloc)
            if is_internal:
                report['links']['internal_count'] += 1
            else:
                report['links']['external_count'] += 1

            if len(report['links']['list']) < 15:
                report['links']['list'].append({
                    'text': link.get_text(strip=True) or '[Image/Empty Link]',
                    'url': full_href,
                    'internal': is_internal
                })

        # 9. Social Metadata
        og_tags = ['title', 'description', 'image', 'url', 'type']
        for tag in og_tags:
            meta = soup.find('meta', property=f'og:{tag}') or soup.find('meta', attrs={'name': f'og:{tag}'})
            if meta and meta.get('content'):
                report['social_metadata'][f'og_{tag}'] = meta['content'].strip()
                report['social_metadata']['has_social'] = True

        twitter_tags = ['card', 'title', 'description', 'image']
        for tag in twitter_tags:
            meta = soup.find('meta', attrs={'name': f'twitter:{tag}'}) or soup.find('meta', attrs={'property': f'twitter:{tag}'})
            if meta and meta.get('content'):
                report['social_metadata'][f'twitter_{tag}'] = meta['content'].strip()
                report['social_metadata']['has_social'] = True

        # 10. robots.txt and sitemap.xml
        parsed_url = urlparse(url)
        root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        robots_data = check_robots_txt(root_url)
        report['files']['robots_exists'] = robots_data['exists']
        report['files']['robots_url'] = robots_data['url']
        report['files']['robots_details'] = robots_data
        
        sitemap_data = check_sitemap_xml(root_url)
        report['files']['sitemap_exists'] = sitemap_data['exists']
        report['files']['sitemap_url'] = sitemap_data['url']
        report['files']['sitemap_details'] = sitemap_data

        # 11. Word Count
        for script in soup(["script", "style"]):
            script.decompose()
        body_text = soup.get_text()
        words = re.findall(r'\w+', body_text)
        word_count = len(words)
        report['performance_metrics']['word_count'] = word_count
        report['performance_metrics']['reading_time_minutes'] = max(1, round(word_count / 200))

        # Keyword density
        stopwords = set(['the', 'and', 'a', 'of', 'to', 'is', 'in', 'that', 'it', 'for', 'on', 'with', 'as', 'this', 'was', 'at', 'by', 'an', 'be', 'are', 'from', 'or', 'you', 'your', 'my', 'we', 'our', 'us', 'i', 'me', 'he', 'she', 'they', 'them', 'its'])
        word_freq = {}
        for w in words:
            wl = w.lower()
            if len(wl) > 3 and wl not in stopwords and not wl.isdigit():
                word_freq[wl] = word_freq.get(wl, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        report['keyword_density'] = [{'keyword': k, 'count': c, 'density': round((c / max(1, word_count)) * 100, 2)} for k, c in sorted_words]

        # SCORING
        score = 0
        
        if report['title']['status'] == 'Good':
            score += 15
        elif report['title']['status'] == 'Warning':
            score += 10
            
        if report['meta_description']['status'] == 'Good':
            score += 15
        elif report['meta_description']['status'] == 'Warning':
            score += 10
            
        if report['canonical']['status'] == 'Good':
            score += 10
            
        if report['viewport_exists']:
            score += 10
            
        if report['files']['robots_exists']:
            score += 10
            
        if report['files']['sitemap_exists']:
            score += 10
            
        h1_count = report['headings']['counts']['h1']
        if h1_count == 1:
            score += 15
        elif h1_count > 1:
            score += 8
        
        img_total = report['images']['total']
        img_missing = report['images']['missing_alt']
        if img_total > 0:
            alt_coverage = (img_total - img_missing) / img_total
            score += round(alt_coverage * 15)
        else:
            score += 15

        if report['index_status']['noindex']:
            score -= 15
            
        if word_count < 300:
            score -= 10
            
        if not report['social_metadata']['has_social']:
            score -= 5

        report['seo_score'] = max(0, min(100, score))
        return report

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch page for SEO analysis: {str(e)}"}