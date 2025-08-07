# Cloud Functions - Yargıtay Scraper
import os
import json
import time
import asyncio
from typing import List, Dict, Any
from flask import Request
from google.cloud import firestore
from google.cloud import secretmanager
import functions_framework
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Initialize Firestore client
db = firestore.Client()

def get_secret(secret_name: str) -> str:
    """Get secret from Google Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get('GCP_PROJECT', 'your-project-id')
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error getting secret {secret_name}: {e}")
        return os.environ.get(secret_name, "")

def setup_chrome_driver():
    """Setup Chrome driver for Cloud Functions"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--ignore-certificate-errors")
    
    return webdriver.Chrome(options=chrome_options)

def scrape_yargitay_keyword(keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Scrape Yargıtay for a specific keyword"""
    results = []
    driver = None
    
    try:
        driver = setup_chrome_driver()
        
        # Navigate to Yargıtay search page
        search_url = "https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/"
        driver.get(search_url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Find search input and enter keyword
        search_input = wait.until(
            EC.presence_of_element_located((By.ID, "txtSearchKeyword"))
        )
        search_input.clear()
        search_input.send_keys(keyword)
        
        # Click search button
        search_button = driver.find_element(By.ID, "btnSearch")
        search_button.click()
        
        # Wait for results
        time.sleep(3)
        
        # Extract results
        result_elements = driver.find_elements(By.CLASS_NAME, "search-result-item")
        
        for i, element in enumerate(result_elements[:max_results]):
            try:
                title_element = element.find_element(By.CLASS_NAME, "result-title")
                content_element = element.find_element(By.CLASS_NAME, "result-content")
                date_element = element.find_element(By.CLASS_NAME, "result-date")
                
                result = {
                    "title": title_element.text.strip(),
                    "content": content_element.text.strip()[:500],  # Limit content
                    "date": date_element.text.strip(),
                    "case_number": f"CASE-{int(time.time())}-{i}",
                    "court": "Yargıtay",
                    "url": f"https://karararama.yargitay.gov.tr/karar/{i}",
                    "keyword": keyword,
                    "scraped_at": time.time()
                }
                results.append(result)
                
            except NoSuchElementException:
                continue
                
    except TimeoutException:
        print(f"Timeout while scraping keyword: {keyword}")
    except Exception as e:
        print(f"Error scraping keyword {keyword}: {e}")
    finally:
        if driver:
            driver.quit()
    
    return results

def cache_results_to_firestore(keyword: str, results: List[Dict[str, Any]]):
    """Cache scraping results to Firestore"""
    try:
        doc_ref = db.collection('scraper_cache').document(keyword)
        doc_ref.set({
            'keyword': keyword,
            'results': results,
            'cached_at': firestore.SERVER_TIMESTAMP,
            'result_count': len(results)
        })
        print(f"Cached {len(results)} results for keyword: {keyword}")
    except Exception as e:
        print(f"Error caching to Firestore: {e}")

def get_cached_results(keyword: str, max_age_hours: int = 24) -> List[Dict[str, Any]]:
    """Get cached results from Firestore"""
    try:
        doc_ref = db.collection('scraper_cache').document(keyword)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            cached_at = data.get('cached_at')
            
            # Check if cache is still valid
            if cached_at:
                cache_age = time.time() - cached_at.timestamp()
                if cache_age < (max_age_hours * 3600):
                    print(f"Using cached results for keyword: {keyword}")
                    return data.get('results', [])
        
        return []
    except Exception as e:
        print(f"Error getting cached results: {e}")
        return []

@functions_framework.http
def scrape_yargitay(request: Request):
    """
    Cloud Function to scrape Yargıtay decisions
    
    Expected request format:
    {
        "keywords": ["keyword1", "keyword2"],
        "max_results": 5,
        "use_cache": true
    }
    """
    # Set CORS headers
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        # Parse request
        if request.method != 'POST':
            return (json.dumps({'error': 'Only POST method allowed'}), 405, headers)
        
        request_json = request.get_json(silent=True)
        if not request_json:
            return (json.dumps({'error': 'Invalid JSON request'}), 400, headers)
        
        keywords = request_json.get('keywords', [])
        max_results = request_json.get('max_results', 5)
        use_cache = request_json.get('use_cache', True)
        
        if not keywords:
            return (json.dumps({'error': 'Keywords are required'}), 400, headers)
        
        # Limit to prevent abuse
        if len(keywords) > 10:
            keywords = keywords[:10]
        
        if max_results > 20:
            max_results = 20
        
        all_results = []
        search_details = {}
        
        for keyword in keywords:
            try:
                # Try cache first
                cached_results = []
                if use_cache:
                    cached_results = get_cached_results(keyword)
                
                if cached_results:
                    results = cached_results[:max_results]
                    search_details[keyword] = {
                        'success': True,
                        'count': len(results),
                        'message': 'Retrieved from cache',
                        'cached': True
                    }
                else:
                    # Scrape fresh data
                    results = scrape_yargitay_keyword(keyword, max_results)
                    
                    # Cache the results
                    if results:
                        cache_results_to_firestore(keyword, results)
                    
                    search_details[keyword] = {
                        'success': True,
                        'count': len(results),
                        'message': 'Scraped fresh data',
                        'cached': False
                    }
                
                all_results.extend(results)
                
            except Exception as e:
                search_details[keyword] = {
                    'success': False,
                    'count': 0,
                    'message': f'Error: {str(e)}',
                    'cached': False
                }
        
        # Remove duplicates based on case_number
        unique_results = {}
        for result in all_results:
            case_number = result.get('case_number', result.get('title', 'unknown'))
            if case_number not in unique_results:
                unique_results[case_number] = result
        
        final_results = list(unique_results.values())
        
        response_data = {
            'success': True,
            'results': final_results,
            'search_details': search_details,
            'total_keywords': len(keywords),
            'unique_results': len(final_results),
            'processing_time': time.time(),
            'message': f'Successfully processed {len(keywords)} keywords, found {len(final_results)} unique results'
        }
        
        return (json.dumps(response_data, ensure_ascii=False), 200, headers)
        
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e),
            'message': 'Internal server error during scraping'
        }
        return (json.dumps(error_response), 500, headers)

# Health check function
@functions_framework.http
def health_check(request: Request):
    """Health check endpoint"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    return (json.dumps({
        'status': 'healthy',
        'service': 'Yargıtay Scraper Function',
        'timestamp': time.time()
    }), 200, headers)

