import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import sys
import os
from urllib.parse import urljoin, urlparse
import re
import html

def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    return re.sub(r'[\\/*?"<>|]', "_", filename)

def get_all_page_urls(base_url):
    """
    Gets all page URLs from a MediaWiki site by scraping the Special:AllPages page.

    Args:
        base_url (str): The base URL of the wiki (e.g., https://en.wikipedia.org).

    Returns:
        list: A list of full URLs for all pages in the wiki.
    """
    all_pages_url = urljoin(base_url, "wiki/Special:AllPages")
    page_urls = []
    
    print(f"Starting to scrape from: {all_pages_url}")

    while all_pages_url:
        try:
            headers = {'User-Agent': 'WikiToPDF/3.0'}
            response = requests.get(all_pages_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error downloading page list: {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_list = soup.find('div', class_='mw-allpages-body')
        if page_list:
            for a in page_list.find_all('a', href=True):
                page_urls.append(urljoin(base_url, a['href']))

        next_page_link = soup.find('a', text=lambda t: t and t.startswith('Next page'))
        if next_page_link:
            all_pages_url = urljoin(base_url, next_page_link['href'])
            print(f"Found next page: {all_pages_url}")
        else:
            all_pages_url = None
            
    return page_urls

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
    page_title = page_url.split('/')[-1].replace('_', ' ')
    sanitized_title = sanitize_filename(page_title)
    filepath = os.path.join(cache_folder, f"{sanitized_title}.txt")

    if not force_download and os.path.exists(filepath):
        print(f"  Loading from cache: {page_title}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return page_title, f.read()

    print(f"  Downloading: {page_url}")
    try:
        headers = {'User-Agent': 'WikiToPDF/3.0'}
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  Error downloading page {page_url}: {e}")
        return page_title, ""

    soup = BeautifulSoup(response.text, 'html.parser')
    content_div = soup.find(id="mw-content-text")
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
        
        print(f"\\nCreating PDF: {pdf_filename}")
        
        for filename in chunk:
            page_title = os.path.splitext(filename)[0]
            filepath = os.path.join(cache_folder, filename)

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            story.append(Paragraph(html.escape(page_title), styles['h1']))
            story.append(Spacer(1, 18))

            for para_text in content.split('\\n\\n'):
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

def download_entire_wiki_to_pdf(base_url, output_filename="full_wiki.pdf"):
    """
    Downloads an entire wiki, caches it to text files, and converts it into a single PDF.

    Args:
        base_url (str): The base URL of the wiki.
        output_filename (str): The name of the output PDF file.
    """
    parsed_url = urlparse(base_url)
    cache_folder = sanitize_filename(parsed_url.netloc + "_wiki")
    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)

    page_urls = get_all_page_urls(base_url)
    
    if not page_urls:
        print("No pages found. Aborting.")
        return

    # Download/cache all pages
    for i, page_url in enumerate(page_urls):
        is_last = (i == len(page_urls) - 1)
        print(f"Processing page {i+1}/{len(page_urls)}")
        get_page_content_and_save(page_url, cache_folder, force_download=is_last)

    # Create PDF from cached files
    styles = getSampleStyleSheet()
    create_pdf_from_cache(cache_folder, output_filename, styles)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        url_to_download = sys.argv[1]
        parsed_url = urlparse(url_to_download)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        safe_file_name = sanitize_filename(parsed_url.netloc) + "_wiki.pdf"
        
        download_entire_wiki_to_pdf(base_url, safe_file_name)
    else:
        print("Usage: python download.py <any_url_from_the_wiki>")
        print("\nNo URL provided. Running with a default example...")
        default_url = "https://terraria.fandom.com/wiki/Terraria_Wiki"
        download_entire_wiki_to_pdf(default_url)
