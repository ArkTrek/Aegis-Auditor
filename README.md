# Aegis Auditor: AI & Security Audit Engine 🛡️🔍

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey.svg)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-HTML%20Parsing-green.svg)

**Aegis Auditor** (formerly Site Auditor) is a free, professional security and SEO hybrid suite designed to generate high-fidelity, interactive reports dynamically for any target host. It acts as a developer utility that extracts public meta tags, heading structures, page sizes, and standard HTTP headers to calculate dynamic SEO and security checklists.

## ✨ Core Features

*   **Concurrent Scanning:** The backend utilizes `ThreadPoolExecutor` to run both the security analyzer and the SEO analyzer concurrently, ensuring fast and efficient report generation. 
*   **Deep Security Posture Analysis:** 
    *   Checks for the presence and validity of SSL/TLS certificates and outdated TLS versions. 
    *   Detects Web Application Firewalls (WAF) such as Cloudflare, AWS CloudFront, and Akamai. 
    *   Audits strict HTTP security headers including HSTS, CSP, X-Frame-Options, and Permissions-Policy. 
    *   Scans for exposed sensitive files and paths like `/.env`, `/.git/config`, and `wp-config.php`. 
*   **Comprehensive SEO Performance Metrics:**
    *   Optionally utilizes a headless Google Chrome instance to fetch and render the DOM accurately. 
    *   Evaluates heading hierarchies (H1-H6), missing image alt text, and the use of modern image formats like WebP or AVIF. 
    *   Checks crawlability via `robots.txt` and `sitemap.xml` parsing, alongside canonical tags and viewport configurations. 
    *   Calculates keyword density, word count, and estimated reading times. 
*   **Interactive Dashboard:** The frontend generates an actionable dashboard featuring executive audit scores, visual gauge charts powered by Chart.js, and prioritized fix recommendations. 
*   **Privacy-First:** The engine performs standard network lookups in real-time, handling data in memory without writing to permanent databases or tracking users with third-party cookies. 

## 🛠️ Tech Stack

*   **Backend Routing:** Flask `3.0.0`. 
*   **Data Extraction & Parsing:** `requests 2.31.0` and `beautifulsoup4 4.12.2`.
*   **Frontend UI:** HTML5, CSS3 with custom variables, and Vanilla JavaScript with HTML5 Canvas animations.
*   **Data Visualization:** Chart.js (via CDN). 

## 🚀 Getting Started

### Prerequisites

*   Python 3.10 or higher.
*   (Optional but recommended) Google Chrome installed on the host machine for accurate DOM rendering during SEO scans.

### Installation

1.  **Clone the repository:**
```bash
    git clone https://github.com/arktrek/aegis-auditor.git
    cd Aegis-Auditor
```

2.  **Create and activate a virtual environment:**
```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3.  **Install the required dependencies:**
```bash
    pip install -r requirements.txt
```

### Running the Engine

Start the local Flask development server:
```bash
python app.py

```

Navigate to `http://127.0.0.1:5000` in your web browser. Enter any target URL (e.g., `google.com`) and click "Run Complete Audit" to generate your report.

## 📂 Project Structure

```text
├── app.py                 # Main Flask routing and concurrent executor
├── requirements.txt       # Pip dependencies
├── scanners/
│   ├── sec_scanner.py     # Logic for SSL, WAF, headers, and sensitive files
│   └── seo_scanner.py     # Logic for DOM parsing, metadata, and crawlability
└── templates/
    ├── index.html         # Main search UI and canvas background
    ├── results.html       # Report dashboard and Chart.js integration
    ├── privacy.html       # Privacy policy details
    └── terms.html         # Terms of service

```

## ⚖️ Terms of Use

By using this software, you agree to only perform scans on domains you own, administer, or have express permission to query. High-frequency automated script calls to the backend scan engine or attempts to conduct DoS attacks are strictly prohibited.

## 👨‍💻 Author

**Arpit Ramesan**
* GitHub: [@ArkTrek](https://github.com/ArkTrek)
* LinkedIn: [Arpit Ramesan](https://www.linkedin.com/in/arpitramesan/)
  
*(Note: Update Privacy Policy and Terms of services as needed. It is currently my own data only.).*
