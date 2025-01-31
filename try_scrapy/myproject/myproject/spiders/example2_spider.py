import scrapy
from urllib.parse import quote

class CaltechSearchSpider(scrapy.Spider):
    name = 'example2'
    allowed_domains = ['caltech.edu']
    
    # List of keywords to search for
    search_keywords = ['quantum', 'neuroscience', 'sustainability']
    
    def start_requests(self):
        base_url = "https://www.caltech.edu/search?q="
        for keyword in self.search_keywords:
            search_url = base_url + quote(keyword)
            yield scrapy.Request(
                url=search_url,
                callback=self.parse_search_results,
                meta={'keyword': keyword}
            )

    def parse_search_results(self, response):
        # Check if there are search results
        if response.css('div.gsc-webResult.gsc-result'):
            # Extract individual search result items
            for result in response.css('div.search-result-item'):
                yield {
                    'keyword': response.meta['keyword'],
                    'title': result.css('h3.result-title a::text').get().strip(),
                    'snippet': ' '.join(result.css('div.result-snippet ::text').getall()).strip(),
                    'url': response.urljoin(result.css('h3.result-title a::attr(href)').get()),
                    'date': result.css('span.result-date::text').get().strip(),
                    'type': result.css('div.result-type::text').get().strip()
                }
                
                # Follow link to full article
                yield response.follow(
                    result.css('h3.result-title a::attr(href)').get(),
                    callback=self.parse_article,
                    meta={
                        'keyword': response.meta['keyword'],
                        'search_title': result.css('h3.result-title a::text').get().strip()
                    }
                )
            
            # Handle pagination
            next_page = response.css('a.pager-next::attr(href)').get()
            if next_page:
                yield response.follow(
                    next_page,
                    callback=self.parse_search_results,
                    meta={'keyword': response.meta['keyword']}
                )

    def parse_article(self, response):
        # Extract main article content
        content = ' '.join(response.css('div.main-content ::text').getall()).strip()
        
        # Check if keyword appears in content (basic relevance check)
        keyword = response.meta['keyword'].lower()
        relevance = keyword in content.lower()
        
        yield {
            'search_keyword': response.meta['keyword'],
            'article_title': response.meta['search_title'],
            'url': response.url,
            'content': content,
            'publish_date': response.css('time.published::attr(datetime)').get(),
            'authors': response.css('span.author-name::text').getall(),
            'relevance_score': relevance,
            'keyword_mentions': content.lower().count(keyword)
        }