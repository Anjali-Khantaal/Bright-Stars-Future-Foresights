import requests
import feedparser
import json

def get_arxiv_articles(query, max_results=10):
    """
    Query arXiv for articles matching the query.
    The arXiv API returns an Atom feed which is parsed using feedparser.
    """
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,  # e.g., "all:energy+OR+all:environment"
        "start": 0,
        "max_results": max_results
    }
    print(f"Fetching arXiv results for query: {query}")
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print("Error fetching from arXiv")
        return []
    
    feed = feedparser.parse(response.text)
    articles = []
    for entry in feed.entries:
        article = {
            "title": entry.title,
            "authors": [author.name for author in entry.authors] if 'authors' in entry else [],
            "summary": entry.summary,
            "published": entry.published,
            "link": entry.link
        }
        articles.append(article)
    return articles

def get_doaj_articles(query, max_results=10):
    """
    Query DOAJ for articles matching the query.
    The DOAJ API accepts a query string via the "q" parameter.
    """
    base_url = "https://doaj.org/api/v1/search/articles"
    params = {
        "q": query,
        "pageSize": max_results
    }
    print(f"Fetching DOAJ results for query: {query}")
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print("Error fetching from DOAJ")
        return []
    
    data = response.json()
    articles = []
    for doc in data.get("results", []):
        bibjson = doc.get("bibjson", {})
        # Some records may not have author info or links
        authors = [author.get("name") for author in bibjson.get("author", [])] if bibjson.get("author") else []
        links = bibjson.get("link", [])
        link_url = links[0].get("url") if links else None
        
        article = {
            "title": bibjson.get("title"),
            "authors": authors,
            "year": bibjson.get("year"),
            "link": link_url
        }
        articles.append(article)
    return articles

def get_semantic_scholar_articles(query, max_results=10):
    """
    Query Semantic Scholar for articles matching the query.
    We request the following fields: title, authors, year, and openAccessPdf.
    Only articles that have an open access PDF URL will be returned.
    
    Note: The Semantic Scholar API is rate-limited and subject to change.
          For extended use or production deployments, consult the API documentation.
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,authors,year,openAccessPdf"
    }
    print(f"Fetching Semantic Scholar results for query: {query}")
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print("Error fetching from Semantic Scholar")
        return []
    
    data = response.json()
    articles = []
    for paper in data.get("data", []):
        open_access = paper.get("openAccessPdf")
        # Only include papers with an open access PDF URL
        if open_access and open_access.get("url"):
            article = {
                "title": paper.get("title"),
                "authors": [author.get("name") for author in paper.get("authors", [])],
                "year": paper.get("year"),
                "openAccessPdf": open_access.get("url")
            }
            articles.append(article)
    return articles

def save_json(filename, data):
    """Helper function to save data to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved data to {filename}")

def main():
    # Define the query. For arXiv, note that the API expects a specific syntax.
    # Here, we search in all fields for "energy" or "environment".
    arxiv_query = "all:energy OR all:environment"
    doaj_query = "energy OR environment"
    semantic_scholar_query = "energy OR environment"

    print("=== arXiv Articles ===")
    arxiv_articles = get_arxiv_articles(arxiv_query, max_results=5)
    print(json.dumps(arxiv_articles, indent=2))
    save_json("arxiv_results.json", arxiv_articles)
    
    print("\n=== DOAJ Articles ===")
    doaj_articles = get_doaj_articles(doaj_query, max_results=5)
    print(json.dumps(doaj_articles, indent=2))
    save_json("doaj_results.json", doaj_articles)
    
    print("\n=== Semantic Scholar Open Access Articles ===")
    ss_articles = get_semantic_scholar_articles(semantic_scholar_query, max_results=5)
    print(json.dumps(ss_articles, indent=2))
    save_json("semantic_scholar_results.json", ss_articles)

if __name__ == "__main__":
    main()
