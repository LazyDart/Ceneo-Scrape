import scrapy

from functools import partial
from ceneoscrape.items import CeneoscrapeItem

import os
import csv

from re import sub, match, search


class CeneoReviewScraperSpider(scrapy.Spider):
    name = "ceneocatselect"
    allowed_domains = ["www.ceneo.pl"]
    start_urls = ["https://www.ceneo.pl/"]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 20, 'DOWNLOAD_DELAY': 0.5}

    # TODO MAKE IT MORE CLASS Like??
    # After Initialization Load all previously saved data id's
    # This will assure no duplicates are generated 
    # and no site will needlessly load.
    offer_refs = set()
    entry_ids = set()    

    # Set current dir as part of Path to easly locate "output.csv"
    os.chdir(os.path.dirname(__file__))

    # output.csv is hard coded, this is a default output name for my programm.
    # If it is found, offer_refs and entry_ids are populated with data.
    if "output.csv" in os.listdir("./"):
        
        # Data is Read using csv library.
        file = open("output.csv")
        olderdata = csv.reader(file)
        for row in olderdata:
            entry_ids.add(row[0])
            offer_refs.add(row[1])
        
        file.close()

    # TODO IMPLEMENT REVIEW COUNTER 
    # For checking balance between positive and negative cases.

    def parse(self, response):
        """
        First Parsing Function

        Loads Ceneo Home-page and reads "most popular categories" link.
        Then opens link to each of those categories.
        TODO: Maybe an option exists to browse all categories. Not only popular ones.
        """

        # .pop-cat-item defines all most popular categories page elements.
        categories = response.css(".pop-cat-item")
        category_links = [selector.attrib["href"] for selector in categories]

        for i in range(len(category_links[8:20])):
            # Get full link to a page by concatenating starting url with single category_link. 
            current_category = self.start_urls[0] + category_links[i]

            # Follow to a Second Parsing Function.
            yield response.follow(current_category, callback=self.parse_category)

        pass

    def parse_category(self, response):
        """
        Second Parsing Function

        Loads Ceneo Category Page with offers listed in a list (around 31 elements).
        Get each of these offers and go to third parsing function.

        Next, go to a next page in the same category and restart the function. 
        """
        # Get contents of all products in category.
        offers = response.css(".cat-prod-row__content")

        passed_counter = 0
        
        # Gather offer-links leading to an offer reviews for each offer.
        # If no link was found ("KeyError") it means that no reviews for product exists. 
        for offer in offers:
            
            try:
                # Review Link - Key Error happens at .attrib["href"]
                offer_link = offer.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl").attrib["href"]

                # Only Offers with review score <5 (negative offers exists) are opened.
                if (("reviews_scroll" in offer_link)  # Seeks only proper review links. 
                    and (r"/Click/Offer" not in offer_link)  # Excludes offers outside of Ceneo
                    and (r"https://redirect.ceneo.pl/offers/" not in offer_link)  # Excludes offers outside of Ceneo
                    and (float(sub("[\n]", "", sub(",", ".", offer.css("span.product-score::text").get()))) < 5)):  # Assure negative offers.
                
                    # TODO Cover limits feature - Limit is unused currently, might be used if offer balance will be more enforced
                    # limit = int(sub("[^0-9]*", "", offer.css("a.product-reviews-link.link.link--accent.js_reviews-link.js_clickHash.js_seoUrl::text").get()))
                    
                    # Extract offer_ref from link.
                    link_ref_match = match("/[0-9]*", offer_link)
                    offer_ref = offer_link[link_ref_match.span()[0]+1:link_ref_match.span()[1]]

                    # If offer_ref wasn't found in previous scrapes then open offer site.
                    if offer_ref not in self.offer_refs:
                        # TODO Skip #tab=reviews_scroll step and use ;0162-0 from the beginning.;
                        
                        offer_link = r"https://www.ceneo.pl/" + offer_ref[:-1] + ";0162-0"
                        self.offer_refs.add(offer_ref)

                        print(offer_link)

                        parse_func = partial(self.parse_offer, limit=max(20, 20))#, limit))
                        
                        yield response.follow(offer_link, callback=parse_func)

            except KeyError:
                # KeyError means offers with 0 reviews were found.
                passed_counter += 1

        # # Go to a next page in the same category.
        # # If Almost all offers have NO REVIEWS (High passed_counter) stop goind to the next pages.
        # next_page = response.css("a.pagination__item.pagination__next")
        # if next_page and (passed_counter < 27):
        #     yield response.follow(self.start_urls[0] + next_page.attrib["href"], callback=self.parse_category)

    def parse_offer(self, response, limit=20):
        """
        Third Parsing Functions. Decides whether enough negative offers are found and follows up to a last scraping function.
        """
        
        # TODO Balanced seek version.
        
        # Used when the limit is used.
        # total_reviews = int(sub("[^0-9]", "", response.css("div.score-extend__review::text")[0].get()))

        # Get counts of all reviews, by their scores. 2 of these counters exist in website, so take only half of values.
        score_percents = response.css("div.js_score-popup-filter-link.score-extend__row")
        score_percents = score_percents[:len(score_percents)//2]

        # Get those values into a dict, divide by 100 to get actual percentage.
        score_dict = {int(score.css("span.score-extend__number::text").get()): float(score.css("span.score-extend__percent::text").get()[:-1])/100 for score in score_percents}

        # If percentage of negative values is greater than 0 then follow up and scrape reviews.
        if score_dict[2] + score_dict[1] > 0:
            
            negatives_scraped = 0

            positive = False

            product_title = response.css("div.product-top__title h1::text").get()

            full_product_category = response.css("nav.js_breadcrumbs.breadcrumbs").css("a.js_breadcrumbs__item.breadcrumbs__item.link span::text").getall()

            top_product_category = full_product_category[-1]

            full_product_category = "/".join(full_product_category[1:])

            reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
            
            # TODO get it into a serializer
            url_match = search("/[0-9]+[;#]", response.request.url)
            current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]-1]
            
            for review in reviews:
                
                # Extract and Format score given by each reviewer. Stop scraping if review has ambiguous score (3)
                current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
                score_match = search("[0-9\.,]+/", current_score)
                current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
                current_score = float(current_score)


                if (((positive and current_score >= 4) 
                    or (not positive and current_score <= 2)) 
                    and (review.attrib["data-entry-id"] not in self.entry_ids)):

                    offer_data = CeneoscrapeItem()

                    # Add Review-Specific Data
                    # Offer refname
                    offer_data["offer_ref"] = current_offer_refname
                
                    # Entry ID
                    offer_data["entry_id"] = review.attrib["data-entry-id"]
                
                    # Review Text
                    offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0].css("div.user-post__text::text").getall())

                    # Score
                    offer_data["score"] = current_score

                    # Extract Dates
                    datetimes = reviews.css("div.user-post__content span.user-post__published time")

                    offer_data["entry_date"] = datetimes[0].attrib["datetime"]
                    offer_data["purchase_date"] = datetimes[1].attrib["datetime"]

                    # Add offer specific data.
                    offer_data["product_title"] = product_title
                    offer_data["full_category"] = full_product_category
                    offer_data["top_category"] = top_product_category

                    negatives_scraped += 1
                    yield offer_data
            
            
            # Create two ways of scraping: Focused on negative and on positive cases
            pos = partial(self.parse_review, positive=True)

            # neg = partial(self.parse_review, positive=False)

            # Call those case-specific functions on offer-sites sorted by positive/negative reviews ";0162-0"
            # yield response.follow(sub("#*tab=reviews_scroll", ";0162-0", str(response.request.url)), callback=neg)

            yield response.follow(sub("#*tab=reviews_scroll", ";0162-1", str(response.request.url)), callback=pos)
            
        else:
            pass
            # TODO if this case is used in anyway, then categories and titles also have to be included here.
            # reviews = response.css("div.user-post.user-post__card.js_product-review")[:3]
            

            # # TODO get it into a serializer
            # url_match = search("/[0-9]+[;#]", response.request.url)
            # current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]-1]


            # for review in reviews:
                
            #     # TODO get it into a serializer
            #     current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
            #     score_match = search("[0-9\,.]+/", current_score)
            #     current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
            #     current_score = float(current_score)

            #     if ((current_score >= 4) or (current_score <= 2)) and (review.attrib["data-entry-id"] not in self.entry_ids):

            #         offer_data = CeneoscrapeItem()

            #         # Offer refname
            #         offer_data["offer_ref"] = current_offer_refname
                
            #         # Entry ID
            #         offer_data["entry_id"] = review.attrib["data-entry-id"]
                
            #         # Review Text
            #         offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0].css("div.user-post__text::text").getall())

            #         offer_data["score"] = current_score
                
            #         yield offer_data

    def parse_review(self, response, positive=False):
        
        # Get offer-specific item features: title/categories

        product_title = response.css("div.product-top__title h1::text").get()

        full_product_category = response.css("nav.js_breadcrumbs.breadcrumbs").css("a.js_breadcrumbs__item.breadcrumbs__item.link span::text").getall()

        top_product_category = full_product_category[-1]

        full_product_category = "/".join(full_product_category[1:])

        reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
        
        # TODO get it into a serializer
        url_match = search("/[0-9]+[;#]", response.request.url)
        current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]-1]
        
        for review in reviews:
            
            # Extract and Format score given by each reviewer. Stop scraping if review has ambiguous score (3)
            current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
            score_match = search("[0-9\.,]+/", current_score)
            current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
            current_score = float(current_score)


            if (((positive and current_score >= 4) 
                or (not positive and current_score <= 2)) 
                and (review.attrib["data-entry-id"] not in self.entry_ids)):

                offer_data = CeneoscrapeItem()

                # Add Review-Specific Data
                # Offer refname
                offer_data["offer_ref"] = current_offer_refname
            
                # Entry ID
                offer_data["entry_id"] = review.attrib["data-entry-id"]
            
                # Review Text
                offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0].css("div.user-post__text::text").getall())

                # Score
                offer_data["score"] = current_score

                # Extract Dates
                datetimes = reviews.css("div.user-post__content span.user-post__published time")

                offer_data["entry_date"] = datetimes[0].attrib["datetime"]
                offer_data["purchase_date"] = datetimes[1].attrib["datetime"]

                # Add offer specific data.
                offer_data["product_title"] = product_title
                offer_data["full_category"] = full_product_category
                offer_data["top_category"] = top_product_category

                yield offer_data