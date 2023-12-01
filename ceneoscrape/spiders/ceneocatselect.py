import scrapy
from re import sub, match
from functools import partial

class CeneocatselectSpider(scrapy.Spider):
    name = "ceneocatselect"
    allowed_domains = ["www.ceneo.pl"]
    start_urls = ["https://www.ceneo.pl/"]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 50, 'DOWNLOAD_DELAY': 0.25}

    offer_refs = set()
    data_gathered = []


    def parse(self, response):
        cats = response.css(".pop-cat-item")
        cat_links = [selector.attrib["href"] for selector in cats]
        cat_titles = [selector.get() for selector in cats.css("a::text")]

        cat_dict = {(cat_titles[i], cat_links[i]) for i in range(len(cats))}
        for i in range(len(cat_links[0:2])):    
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
                offer_link = offer.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl").attrib["href"]
                # offer_link = offer.css("span a").attrib["href"]

            # offer_score = float(sub("[\n]", "", sub(",", ".", offer.css("span.product-score::text").get())))

                if ("reviews_scroll" in offer_link) and (float(sub("[\n]", "", sub(",", ".", offer.css("span.product-score::text").get()))) < 5):

                    # if len(offer.css(".cat-prod-row__name").css("span:not([class=label])::text").get()) == 2:
                    #     offer_title = offer.css(".cat-prod-row__name").css("span:not([class=label])::text")[1].get()
                    # else:
                    #     offer_title = offer.css(".cat-prod-row__name").css("span:not([class=label])::text").get()
                    
                # [offer.get() for offer in  offers.css("span a")]
                
                # [offer.css("::text").get() for offer in response.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl")]
                # [offer.attrib["href"] for offer in response.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl")]
                
                    # TODO if Reviews > 1
                    if (r"/Click/Offer" not in offer_link) and (r"https://redirect.ceneo.pl/offers/" not in offer_link):
                        

                        limit = int(sub("[^0-9]*", "", offer.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl::text").get()))
                        # print(offer_title, sub("#*tab=reviews_scroll", ";0162-0", offer_link))
                        # print(offer_title, offer_link)

                        link_ref_match = match("/[0-9]*", offer_link)
                        offer_ref = offer_link[link_ref_match.span()[0]+1:link_ref_match.span()[1]]


                        if offer_ref not in self.offer_refs:
                            offer_link = r"https://www.ceneo.pl/" + offer_ref + "#tab=reviews_scroll" 
                            # offer_dict[offer_title] = offer_link

                            self.offer_refs.add(offer_ref)

                            parse_func = partial(self.parse_offer, limit=max(20, limit))
                            
                            yield response.follow(offer_link, callback=parse_func)

            except KeyError:
                print("Passed")

                # offer_titles = [selector.get() for selector in offers.css("span:not([class])::text")]
            # offer_links = [selector.css("a").attrib["href"] for selector in offers]
            
            # offer_dict = {(offer_titles[i], offer_links[i]) for i in range(len(offers))}

            

    def parse_offer(self, response, limit=20):
        # 1: Document Offer Name
        # 2: Document reviews and their entry id
        # 3: Pick Balanced number of reviews

        # TODO Balanced seek version.
        # Data Storing and saving.
        

        total_reviews = int(sub("[^0-9]", "", response.css("div.score-extend__review::text")[0].get()))

        score_percents = response.css("div.js_score-popup-filter-link.score-extend__row")
        score_percents = score_percents[:len(score_percents)//2]
        score_dict = {int(score.css("span.score-extend__number::text").get()): float(score.css("span.score-extend__percent::text").get()[:-1])/100 for score in score_percents}

        if score_dict[2] + score_dict[1] < 0.01:
            reviews = response.css("div.user-post.user-post__card.js_product-review")[:3]
            #             entry_ids = [selector.css("a.link.link--accent.user-post__abuse.js_report-product-review-abuse").attrib["data-review-id"] for selector in reviews]
            
            entry_ids = []
            review_text = []
            scores = []
            for review in reviews:
            # Entry ID
                entry_ids.append(review.attrib["data-entry-id"])
            
            # reviews = reviews.css("div.user-post__content")[::2]
            # Review Text
                review_text.append(review.css("div.user-post__content")[0].css("div.user-post__text::text").get())

            # Score
                scores.append(review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get())

            print(entry_ids, [text[:10] for text in review_text], len(scores), response.request.url)
        else:
            yield response.follow(sub("#*tab=reviews_scroll", ";0162-0", str(response.request.url)), callback=self.parse_pos_or_neg)

            yield response.follow(sub("#*tab=reviews_scroll", ";0162-1", str(response.request.url)), callback=self.parse_pos_or_neg)


        # else:
        #     pass


        pass

    def parse_pos_or_neg(self, response):
        reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
            #             entry_ids = [selector.css("a.link.link--accent.user-post__abuse.js_report-product-review-abuse").attrib["data-review-id"] for selector in reviews]

        entry_ids = []
        review_text = []
        scores = []
        for review in reviews:
        # Entry ID
            entry_ids.append(review.attrib["data-entry-id"])
        
        # reviews = reviews.css("div.user-post__content")[::2]
        # Review Text
            review_text.append(review.css("div.user-post__content")[0].css("div.user-post__text::text").get())

        # Score
            scores.append(review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get())

        # TODO Add score filtering if ;0162-0 only score <= 2 if ;0162-1 only score >= 4
        print("HOOOLY XDDDDDD\n",entry_ids, [text[:10] for text in review_text], len(scores), response.request.url)
        
        
#TODO
# add #tab=reviews_scroll
# or ;0162-0 <- negative and ;0162-1 <- positive