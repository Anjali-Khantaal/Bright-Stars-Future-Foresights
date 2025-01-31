import scrapy

class ExampleSpider(scrapy.Spider):
    name = 'example'
    start_urls = ['https://www.caltech.edu']

    def parse(self, response):
        for article in response.css('div.events-block__events__event.pb-4'):
            # First get the relative link properly
            relative_url = article.css('a.events-block__events__event__title__link::attr(href)').get()
            
            # Create absolute URL using response.urljoin
            absolute_url = response.urljoin(relative_url)
            
            # Extract title from LISTING PAGE (not detail page)
            event_title = article.css('a.events-block__events__event__title__link::text').get().strip()

            # Yield request to follow the link
            yield response.follow(
                absolute_url,
                callback=self.parse_article,
                meta={'title': event_title}  # Use the title from listing page
            )

    def parse_article(self, response):
        # Extract content from detail page
        yield {
            'title': response.meta.get('title'),
            'content': ' '.join(response.css('div.rich-text ::text').getall()).strip(),
            # Added important elements
            'url': response.url,
            'date': response.css('div.event-page__details__date-time__line::text').get().strip(),
            'location': response.css('a.event-page__details__location.d-inline-block.mb-2::text').get()
        }