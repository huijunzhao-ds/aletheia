import logging
import datetime
import httpx
import urllib.parse
import re
import arxiv
from typing import List, Dict, Optional


logger = logging.getLogger(__name__)

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


def search_arxiv(query: str, max_results: int = 5, sort_by_date: bool = False, published_after: Optional[datetime.datetime] = None) -> List[Dict[str, str]]:
    """
    Search for papers on arXiv.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        sort_by_date: If True, sorts by latest submitted date. Otherwise sorts by relevance.
        published_after: Optional datetime. If provided, excludes papers published before this time.
        
    Returns:
        A list of dictionaries containing paper details (title, summary, authors, pdf_url).
    """
    # If published_after is set, we want ALL papers in that window, so we uncap max_results
    # The loop will terminate based on the date check or server-side filter.
    search_max_results = float('inf') if published_after else max_results

    # Configure client with retries and optimized page size
    # If max_results is distinct, scale page size. If infinite/all, use 100.
    if search_max_results and search_max_results != float('inf'):
         page_size = min(search_max_results * 4, 100) if search_max_results > 0 else 100
    else:
         page_size = 100

    client = arxiv.Client(
        page_size=page_size,
        delay_seconds=3.0,
        num_retries=3
    )
    
    # Construct the final query with server-side date filtering if applicable
    final_query = query.strip() if query else ""
    
    if published_after:
        # ArXiv API format: YYYYMMDDHHMM
        # We construct a range from published_after to a far future date
        start_date = published_after.strftime("%Y%m%d%H%M")
        # Use a reasonable future year to cover "now"
        end_date = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y%m%d%H%M")
        
        date_filter = f"submittedDate:[{start_date} TO {end_date}]"
        
        if final_query:
            # Group original query to ensure boolean logic works as expected (Query AND Date)
            final_query = f"({final_query}) AND {date_filter}"
        else:
            final_query = date_filter

    if not final_query:
        logger.warning("Arxiv search called with empty query and no date filter.")
        return []

    sort_criterion = arxiv.SortCriterion.SubmittedDate if sort_by_date else arxiv.SortCriterion.Relevance
    
    # arxiv library documentation says: max_results (int): ... default is 10.
    # Current implementation of python-arxiv (v2.x) uses a generator. 
    # Passing float('inf') might crash it if it expects int. 
    # Let's use a standard explicit check.
    _limit = search_max_results if (search_max_results and search_max_results != float('inf')) else None

    search = arxiv.Search(
        query=final_query,
        max_results=_limit,
        sort_by=sort_criterion
    )
    
    results = []
    try:
        # Execute search
        # Note: We trust the server-side date filter, but we also double-check 
        # because the API can sometimes be fuzzy or return 'updated' dates that differ.
        for result in client.results(search):
            
            # Additional client-side safety check for date
            if published_after:
                res_date = result.published
                if not res_date.tzinfo:
                    res_date = res_date.replace(tzinfo=datetime.timezone.utc)
                
                check_date = published_after
                if not check_date.tzinfo:
                    check_date = check_date.replace(tzinfo=datetime.timezone.utc)

                if res_date < check_date:
                    # If we find a paper older than the cutoff
                    if sort_by_date:
                        # Optimization: if sorted by date, all subsequent are older
                        break
                    # Otherwise (Relevance sort), just skip this one
                    continue

            results.append({
                "title": result.title,
                "summary": result.summary,
                "authors": [a.name for a in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url
            })
            
    except Exception as e:
        logger.error(f"Error searching arXiv: {e}")
        # Return whatever we found so far instead of empty list if possible, or just empty
        return results
        
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
