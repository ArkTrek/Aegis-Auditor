from flask import Flask, render_template, request, redirect, url_for
from scanners.sec_scanner import analyze_security
from scanners.seo_scanner import analyze_seo
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan():
    target_url = request.form.get('url')
    
    if not target_url:
        return redirect(url_for('index'))

    # Run both scanners concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_sec = executor.submit(analyze_security, target_url)
        future_seo = executor.submit(analyze_seo, target_url)
        security_results = future_sec.result()
        seo_results = future_seo.result()
    
    # Pass both reports to the results template
    return render_template(
        'results.html', 
        target_url=target_url,
        sec_report=security_results,
        seo_report=seo_results
    )

@app.route('/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')

@app.route('/terms', methods=['GET'])
def terms():
    return render_template('terms.html')

if __name__ == '__main__':
    app.run(debug=True)