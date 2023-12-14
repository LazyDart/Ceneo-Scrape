# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CeneoscrapeItem(scrapy.Item):
    # All features all passed as strings except for score.
    entry_id = scrapy.Field()  # Unique id of each review.
    review_text = scrapy.Field()  # Content of a review
    score = scrapy.Field()  # Score of a review (0-2) Considered Pos and (4-5) Considered Neg
    offer_ref = scrapy.Field()  # Unique id of each offer.
    purchase_date = scrapy.Field()  # User's Date of Purchase
    entry_date = scrapy.Field()  # User's Date of Review
    product_title = scrapy.Field()  # Product Title
    full_category = scrapy.Field()  # Complete Category tree like: "Ceneo/Biuro/Sprzet/Projektory" etc.
    top_category = scrapy.Field()  # The top category from category tree i.e. "Projektory"
