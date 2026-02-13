import logging
import datetime
import httpx
import urllib.parse
import re
import arxiv
import time
import threading
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Global lock for arXiv API to enforce 1 request at a time and 3s delay
_ARXIV_LOCK = threading.Lock()
_LAST_ARXIV_CALL = 0.0

def web_search(query: str) -> str:
    """
    Search Google to find information on the web.
    Use this for general knowledge, news, and current events.
    
    Args:
        query: The search query.
        
    Returns:
        The search results as a string.
    """
    try:
        # We use a direct HTTP lookup to avoid complex internal ADK context mismatches
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                # Basic snippet extraction from the HTML results
                html = response.text
                
                # Remove scripts and styles to save tokens
                html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
                html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL)
                
                # Remove HTML tags to get raw text
                text = re.sub(r'<[^>]+>', ' ', html)
                
                # Normalize whitespace
                text = ' '.join(text.split())
                
                # We return the top portion of the CLEANED text
                return text
            else:
                return f"Search returned status code {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error in web_search: {e}")
        return f"Search failed: {e}"


def search_arxiv(query: str, max_results: int = 5, published_after: Optional[datetime.datetime] = None) -> List[Dict[str, str]]:
    """
    Search for papers on arXiv.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        published_after: Optional datetime. If provided, excludes papers published before this time.
        
    Returns:
        A list of dictionaries containing paper details (title, summary, authors, pdf_url).
    """
    global _LAST_ARXIV_CALL
    
    # If published_after is set, we want ALL papers in that window, so we uncap max_results
    # The loop will terminate based on the date check or server-side filter.
    search_max_results = None if published_after else max_results

    # Configure client with retries and optimized page size
    # If max_results is distinct, scale page size. If infinite/all, use 100.
    if search_max_results:
         page_size = min(search_max_results * 4, 100) if search_max_results and search_max_results > 0 else 100
    else:
         page_size = 100

    # Use slightly higher delay in client config, though our global lock handles the primary delay.
    client = arxiv.Client(page_size=page_size, delay_seconds=5.0, num_retries=5)

    final_query = query.strip() if query else ""
    if published_after:
        start_date = published_after.strftime("%Y%m%d%H%M")
        # Use a reasonable future year to cover "now"
        end_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y%m%d%H%M")
        date_filter = f"submittedDate:[{start_date} TO {end_date}]"
        
        if final_query:
            # Group original query to ensure boolean logic works as expected (Query AND Date)
            final_query = f"({final_query}) AND {date_filter}"
        else:
            final_query = date_filter
    if not final_query:
        logger.warning("Arxiv search called with empty query and no date filter.")
        return []
    
    search = arxiv.Search(query=final_query, max_results=search_max_results, sort_by=arxiv.SortCriterion.SubmittedDate)
    
    max_retries = 3
    
    # ACQUIRE GLOBAL LOCK
    with _ARXIV_LOCK:
        # Enforce 3.0s delay since last call
        elapsed = time.time() - _LAST_ARXIV_CALL
        if elapsed < 4.5:
            delay = 4.5 - elapsed
            logger.info(f"ArXiv rate limit enforcement: Sleeping for {delay:.2f}s")
            time.sleep(delay)
            
        try:
            for attempt in range(max_retries):
                results = []
                try:
                    # Update timestamp before making the request
                    _LAST_ARXIV_CALL = time.time()
                    
                    for result in client.results(search):
                        if published_after:
                            res_date = result.published
                            if not res_date.tzinfo:
                                res_date = res_date.replace(tzinfo=datetime.timezone.utc)
                            
                            check_date = published_after
                            if not check_date.tzinfo:
                                check_date = check_date.replace(tzinfo=datetime.timezone.utc)

                            if res_date < check_date:
                                break
                    
                        results.append({
                            "title": result.title,
                            "summary": result.summary,
                            "authors": [a.name for a in result.authors],
                            "published": result.published.strftime("%Y-%m-%d"),
                            "pdf_url": result.pdf_url
                        })
                    
                    # If successful, return immediately
                    return results
                        
                except Exception as e:
                    is_rate_limit = "429" in str(e)
                    if is_rate_limit and attempt < max_retries - 1:
                        wait_seconds = 5 * (2 ** attempt) # 5, 10, 20...
                        logger.warning(f"ArXiv 429 rate limit. Retrying in {wait_seconds}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(wait_seconds)
                        continue
                    
                    logger.error(f"Error searching arXiv: {e}")
                    # Return whatever we found so far in this attempt
                    return results
            
        except Exception as e:
            logger.error(f"Unexpected error in search_arxiv: {e}")
            return []
            
    return results

def scrape_website(url: str) -> str:
    """
    Fetches and extracts text content from a given URL.
    Use this to collect articles, blog posts, or documentation.
    
    Args:
        url: The URL to scrape.
        
    Returns:
        The text content of the website.
    """
    try:
        # User defined headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            # Simple text extraction (stripping HTML tags)
            # In a real app, use BeautifulSoup
            html = response.text
            # Remove scripts and styles
            html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL)
            # Remove tags
            text = re.sub(r'<[^>]+>', ' ', html)
            # Normalize whitespace
            text = ' '.join(text.split())
            
            return text[:20000] # Limit content size
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return f"Failed to read content from {url}: {e}"
