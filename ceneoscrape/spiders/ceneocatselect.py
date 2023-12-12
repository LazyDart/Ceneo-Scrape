import os
import csv

from re import sub, match, search

import scrapy

from functools import partial
from ceneoscrape.items import CeneoscrapeItem


class CeneocatselectSpider(scrapy.Spider):
    name = "ceneocatselect"
    allowed_domains = ["www.ceneo.pl"]
    start_urls = ["https://www.ceneo.pl/"]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 50, 'DOWNLOAD_DELAY': 0.25}
    offer_refs = set()
    entry_ids = set()    

    # TODO MAKE IT MORE CLASS Like??
    os.chdir(os.path.dirname(__file__))

    if "output.csv" in os.listdir("./"):
        file = open("output.csv")
        olderdata = csv.reader(file)
        for row in olderdata:
            entry_ids.add(row[0])
            offer_refs.add(row[1])
        file.close()

    def parse(self, response):
        cats = response.css(".pop-cat-item")
        cat_links = [selector.attrib["href"] for selector in cats]

        # Category item??
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

        passed_counter = 0
        # Offer ITEM?
        for offer in offers:
            
            try:
                offer_link = offer.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl").attrib["href"]

                if ("reviews_scroll" in offer_link) and (float(sub("[\n]", "", sub(",", ".", offer.css("span.product-score::text").get()))) < 5):
                    
                    if (r"/Click/Offer" not in offer_link) and (r"https://redirect.ceneo.pl/offers/" not in offer_link):
                        

                        limit = int(sub("[^0-9]*", "", offer.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl::text").get()))
                        
                        link_ref_match = match("/[0-9]*", offer_link)
                        offer_ref = offer_link[link_ref_match.span()[0]+1:link_ref_match.span()[1]]


                        if offer_ref not in self.offer_refs:
                            offer_link = r"https://www.ceneo.pl/" + offer_ref + "#tab=reviews_scroll" 
                            
                            self.offer_refs.add(offer_ref)

                            parse_func = partial(self.parse_offer, limit=max(20, limit))
                            
                            yield response.follow(offer_link, callback=parse_func)

            except KeyError:
                print("Passed")
                passed_counter += 1

        next_page = response.css("a.pagination__item.pagination__next")
        if next_page and (passed_counter < 27):
            print("GOING TO THE NEXT PAGE")
            yield response.follow(self.start_urls[0] + next_page.attrib["href"], callback=self.parse_category)

    def parse_offer(self, response, limit=20):
        # 3: Pick Balanced number of reviews

        # TODO Balanced seek version.
        # Data Storing and saving.
        
        total_reviews = int(sub("[^0-9]", "", response.css("div.score-extend__review::text")[0].get()))

        score_percents = response.css("div.js_score-popup-filter-link.score-extend__row")
        score_percents = score_percents[:len(score_percents)//2]
        score_dict = {int(score.css("span.score-extend__number::text").get()): float(score.css("span.score-extend__percent::text").get()[:-1])/100 for score in score_percents}

        if score_dict[2] + score_dict[1] < 0.01:
            reviews = response.css("div.user-post.user-post__card.js_product-review")[:3]
            

            # TODO get it into a serializer
            url_match = search("/[0-9]+[;#]", response.request.url)
            current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]-1]


            for review in reviews:
                
                # TODO get it into a serializer
                current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
                score_match = search("[0-9\,.]/", current_score)
                current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
                current_score = float(current_score)

                if ((current_score >= 4) or (current_score <= 2)) and (review.attrib["data-entry-id"] not in self.entry_ids):

                    offer_data = CeneoscrapeItem()

                    # Offer refname
                    offer_data["offer_ref"] = current_offer_refname
                
                    # Entry ID
                    offer_data["entry_id"] = review.attrib["data-entry-id"]
                
                    # Review Text
                    offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0].css("div.user-post__text::text").getall())

                    offer_data["score"] = current_score
                
                    yield offer_data

        else:
            pos = partial(self.parse_review, positive=True)
            neg = partial(self.parse_review, positive=False)
            yield response.follow(sub("#*tab=reviews_scroll", ";0162-0", str(response.request.url)), callback=pos)

            yield response.follow(sub("#*tab=reviews_scroll", ";0162-1", str(response.request.url)), callback=neg)


        pass

    def parse_review(self, response, positive=False):
        # TODO filtering pos/neg

        reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
        
        # TODO get it into a serializer
        url_match = search("/[0-9]+[;#]", response.request.url)
        current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]-1]
        
        for review in reviews:
            
            # TODO get it into a serializer
            current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
            score_match = search("[0-9\.,]/", current_score)
            current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
            current_score = float(current_score)

            if ((positive and current_score >= 4) or (not positive and current_score <= 2)) and (review.attrib["data-entry-id"] not in self.entry_ids):

                offer_data = CeneoscrapeItem()

                # Offer refname
                offer_data["offer_ref"] = current_offer_refname
            
                # Entry ID
                offer_data["entry_id"] = review.attrib["data-entry-id"]
            
                # Review Text
                offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0].css("div.user-post__text::text").getall())

                offer_data["score"] = current_score

                yield offer_data
        
        # self.data_gathered += [[entry_ids[i], scores[i], review_text[i][:15]] for i in range(len(entry_ids)) if (scores[i] >= 4 and positive) or (scores[i] <= 2 and not positive)]
        