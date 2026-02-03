# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    domain = scrapy.Field()
    title = scrapy.Field()
    headings = scrapy.Field()
    paragraphs = scrapy.Field()
    tables = scrapy.Field()
    meta_desc = scrapy.Field()
    media_links = scrapy.Field()
