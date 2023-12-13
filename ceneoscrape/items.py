# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CeneoscrapeItem(scrapy.Item):
    entry_id = scrapy.Field()  # Entry ID of a Review
    review_text = scrapy.Field()  # Text of a Review 
    score = scrapy.Field()  # Score of a review (0-2) Pos or (4-5) Neg
    offer_ref = scrapy.Field()  # Ref name of an Offer
    purchase_date = scrapy.Field()  # Date of Purchase
    entry_date = scrapy.Field()  # Date of Review
    product_title = scrapy.Field()  # Product Title
    full_category = scrapy.Field()
    top_category = scrapy.Field()    
