import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import sys
import os
from urllib.parse import urljoin, urlparse, parse_qs
import re
import html
import json
import time

# List of URL endings to ignore
IGNORED_URL_ENDINGS = ["/cs"]
# Delay between downloads in seconds
DOWNLOAD_DELAY = .1

def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    return re.sub(r'[\\/*?"<>|]', "_", filename)

def get_all_page_urls(base_url):
    """
    Gets all page URLs from a MediaWiki site using the API.

    Args:
        base_url (str): The base URL of the wiki (e.g., https://en.wikipedia.org).

    Returns:
        list: A list of full URLs for all pages in the wiki.
    """
    api_url = urljoin(base_url, "api.php")
    page_urls = []
    params = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "aplimit": "max"
    }

    print(f"Fetching page list from API: {api_url}")

    while True:
        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error querying API: {e}")
            break
        except json.JSONDecodeError:
            print("Error decoding JSON from API response.")
            break

        pages = data.get("query", {}).get("allpages", [])
        for page in pages:
            title = page["title"]
            page_url = urljoin(api_url, f"index.php?title={title.replace(' ', '_')}")
            page_urls.append(page_url)

        if "continue" in data:
            params["apcontinue"] = data["continue"]["apcontinue"]
            print(f"  ...continuing with next batch of pages.")
            time.sleep(DOWNLOAD_DELAY)
        else:
            break
    
    # Filter out ignored URLs
    filtered_urls = [url for url in page_urls if not any(url.endswith(ending) for ending in IGNORED_URL_ENDINGS)]
    print(f"Found {len(page_urls)} pages, {len(filtered_urls)} after filtering.")

    return filtered_urls

def get_page_content_and_save(page_url, cache_folder, force_download=False):
    """
    Gets the content of a single page, either from cache or by downloading.
    Saves the content to a text file.

    Args:
        page_url (str): The URL of the page to process.
        cache_folder (str): The path to the folder where text files are stored.
        force_download (bool): If True, always downloads the page even if it exists in cache.

    Returns:
        tuple: (page_title, page_text_content)
    """
    parsed_url = urlparse(page_url)
    query_params = parse_qs(parsed_url.query)
    if 'title' in query_params:
        page_title = query_params['title'][0].replace('_', ' ')
    else:
        page_title = page_url.split('/')[-1].replace('_', ' ') # Fallback

    sanitized_title = sanitize_filename(page_title)
    filepath = os.path.join(cache_folder, f"{sanitized_title}.txt")

    if not force_download and os.path.exists(filepath):
        print(f"  Loading from cache: {page_title}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return page_title, f.read()

    print(f"  Downloading: {page_url}")
    try:
        time.sleep(DOWNLOAD_DELAY)
        headers = {'User-Agent': 'WikiToPDF/3.0'}
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  Error downloading page {page_url}: {e}")
        return page_title, ""

    soup = BeautifulSoup(response.text, 'html.parser')
    content_div = soup.find(id="mw-content-text")
    if not content_div:
        # Fallback for wikis that might not have mw-content-text
        content_div = soup.find('div', class_='mw-parser-output')
        if not content_div:
            return page_title, ""

    # Remove unwanted elements
    for unwanted in content_div.find_all(['div', 'table', 'ul', 'ol', 'span', 'img', 'figure'],
                                         class_=['toc', 'navbox', 'infobox', 'reflist',
                                                 'mw-references-columns', 'mw-editsection', 'gallery', 'thumb']):
        unwanted.decompose()

    page_text = content_div.get_text()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(page_text)

    return page_title, page_text

def create_pdf_from_cache(cache_folder, pdf_output_folder, styles):
    """
    Creates PDFs from the text files in the cache folder, with 100 pages per PDF.

    Args:
        cache_folder (str): The path to the folder where text files are stored.
        pdf_output_folder (str): The path to the folder where PDFs will be saved.
        styles (StyleSheet): The stylesheet to use for the PDF.
    """
    text_files = sorted([f for f in os.listdir(cache_folder) if f.endswith(".txt")])
    
    for i in range(0, len(text_files), 100):
        chunk = text_files[i:i+100]
        
        if not chunk:
            continue

        first_file_name = os.path.splitext(chunk[0])[0]
        last_file_name = os.path.splitext(chunk[-1])[0]
        
        pdf_filename = f"{first_file_name}_to_{last_file_name}.pdf"
        pdf_filepath = os.path.join(pdf_output_folder, pdf_filename)
        
        doc = SimpleDocTemplate(pdf_filepath, pagesize=letter)
        story = []
        
        print(f"\nCreating PDF: {pdf_filename}")
        
        for filename in chunk:
            page_title = os.path.splitext(filename)[0]
            filepath = os.path.join(cache_folder, filename)

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            story.append(Paragraph(html.escape(page_title), styles['h1']))
            story.append(Spacer(1, 18))

            for para_text in content.split('\n\n'):
                para_text = para_text.strip()
                if para_text:
                    story.append(Paragraph(html.escape(para_text), styles['BodyText']))
                    story.append(Spacer(1, 8))
            
            story.append(PageBreak())
            
        try:
            doc.build(story)
            print(f"  Successfully created: {pdf_filename}")
        except Exception as e:
            print(f"  Error building PDF {pdf_filename}: {e}")

def download_entire_wiki_to_pdf(base_url):
    """
    Downloads an entire wiki, caches it to text files, and converts it into multiple PDFs.

    Args:
        base_url (str): The base URL of the wiki.
    """
    parent_folder = "all_wiki"
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)

    parsed_url = urlparse(base_url)
    sanitized_domain = sanitize_filename(parsed_url.netloc)
    cache_folder = os.path.join(parent_folder, f"{sanitized_domain}_txt")
    pdf_output_folder = os.path.join(parent_folder, f"{sanitized_domain}_wiki_PDF")

    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)
    if not os.path.exists(pdf_output_folder):
        os.makedirs(pdf_output_folder)

    page_urls = get_all_page_urls(base_url)
    
    if not page_urls:
        print("No pages found. Aborting.")
        return

    # Download/cache all pages
    for i, page_url in enumerate(page_urls):
        is_last = (i == len(page_urls) - 1)
        print(f"Processing page {i+1}/{len(page_urls)}")
        get_page_content_and_save(page_url, cache_folder, force_download=is_last)

    # Create PDFs from cached files
    styles = getSampleStyleSheet()
    create_pdf_from_cache(cache_folder, pdf_output_folder, styles)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        url_to_download = sys.argv[1]
        parsed_url = urlparse(url_to_download)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        download_entire_wiki_to_pdf(base_url)
    else:
        print("Usage: python download.py <any_url_from_the_wiki>")
        print("\nNo URL provided. Running with a default example...")
        default_url = "https://vampire.survivors.wiki/"
        download_entire_wiki_to_pdf(default_url)
