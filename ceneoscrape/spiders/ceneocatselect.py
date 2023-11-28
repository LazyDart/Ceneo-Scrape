import scrapy
from re import sub
from functools import partial

class CeneocatselectSpider(scrapy.Spider):
    name = "ceneocatselect"
    allowed_domains = ["www.ceneo.pl"]
    start_urls = ["https://www.ceneo.pl/"]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 30}


    def parse(self, response):
        cats = response.css(".pop-cat-item")
        cat_links = [selector.attrib["href"] for selector in cats]
        cat_titles = [selector.get() for selector in cats.css("a::text")]

        cat_dict = {(cat_titles[i], cat_links[i]) for i in range(len(cats))}
        for i in range(len(cat_links)):    
            current_cat = self.start_urls[0] + cat_links[i]

            yield response.follow(current_cat, callback=self.parse_category)

        pass

    def parse_category(self, response):
        offers = response.css(".cat-prod-row__content")
        
        # TODO IMPLEMENT REVIEW COUNTER 
        # For checking balance between positive and negative cases.

        offer_dict = {}

        for offer in offers:
            # Exclude /Click/Offer    https://redirect.ceneo.pl/offers/
            try:
                offer_link = offer.css("span a").attrib["href"]
                limit = int(sub("[^0-9]*", "", offer.css("span a::text").get()))

            # offer_score = float(sub("[\n]", "", sub(",", ".", offer.css("span.product-score::text").get())))

                if ("reviews_scroll" in offer_link) and (float(sub("[\n]", "", sub(",", ".", offer.css("span.product-score::text").get()))) < 5):

                    if len(offer.css(".cat-prod-row__name").css("span:not([class=label])::text").get()) == 2:
                        offer_title = offer.css(".cat-prod-row__name").css("span:not([class=label])::text")[1].get()
                    else:
                        offer_title = offer.css(".cat-prod-row__name").css("span:not([class=label])::text").get()
                    
                # [offer.get() for offer in  offers.css("span a")]
                
                    
                
                    # TODO if Reviews > 1
                    if (r"/Click/Offer" not in offer_link) and (r"https://redirect.ceneo.pl/offers/" not in offer_link):

                        print(offer_title, sub("#*tab=reviews_scroll", ";0162-0", offer_link))
                        # print(offer_title, offer_link)
                    
                        offer_dict[offer_title] = offer_link
            except KeyError:
                print("Passed")

                # offer_titles = [selector.get() for selector in offers.css("span:not([class])::text")]
            # offer_links = [selector.css("a").attrib["href"] for selector in offers]
            
            # offer_dict = {(offer_titles[i], offer_links[i]) for i in range(len(offers))}

            parse_func = partial(self.parse_offer, limit=max(20, limit))
            # yield response.follow(offer_link, callback=self.parse_category)

    def parse_offer(self, response, limit=20):
        # 1: Document Offer Name
        # 2: Document reviews and their entry id
        # 3: Pick Balanced number of reviews
        
        # Entry ID
        # [selector.attrib["data-entry-id"] for selector in response.css("div.user-post.user-post__card.js_product-review")]
        
        # Review Text
        #[selector.css("div.user-post__text::text").get() for selector in response.css("div.user-post.user-post__card.js_product-review")]

        # Score
        #[selector.css("span.user-post__score-count::text").get() for selector in response.css("div.user-post.user-post__card.js_product-review")]

        # offers = response.css(".cat-prod-row__name")
        
        # offer_dict = {}

        # for offer in offers:
        #     # Exclude /Click/Offer    https://redirect.ceneo.pl/offers/

        #     if len(offer.css("span:not([class=label])::text")) == 2:
        #         offer_title = offer.css("span:not([class=label])::text")[1].get()
        #     else:
        #         offer_title = offer.css("span:not([class=label])::text").get()
        #     offer_link = offer.css("a").attrib["href"]
            
        #     if (r"/Click/Offer" not in offer_link) and (r"https://redirect.ceneo.pl/offers/" not in offer_link):
                 
            
        #         print(offer_title, offer_link)
            
        #     offer_dict[offer_title] = offer_link
        #     # offer_titles = [selector.get() for selector in offers.css("span:not([class])::text")]
        #     # offer_links = [selector.css("a").attrib["href"] for selector in offers]
            
        #     # offer_dict = {(offer_titles[i], offer_links[i]) for i in range(len(offers))}

        # print(len(offer_dict))

        pass

#TODO
# add #tab=reviews_scroll
# or ;0162-0 <- negative and ;0162-1 <- positive