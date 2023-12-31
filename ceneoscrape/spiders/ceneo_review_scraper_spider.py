import scrapy

from functools import partial
from ceneoscrape.items import CeneoscrapeItem

import os
import csv

from re import sub, match, search
from itertools import chain

class CeneoReviewScraperSpider(scrapy.Spider):
    name = "ceneocatselect"
    allowed_domains = ["www.ceneo.pl"]
    start_urls = ["https://www.ceneo.pl/"]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 1000, 'DOWNLOAD_DELAY': 1}

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
        
        # Get All categories sub menus
        sub_menus = response.css("div.js_cat-menu-item.cat-menu-item")
        
        # For each menu excluding jewelry, fashion and erotic get all sub-categories
        sub_menus = [menu for menu in sub_menus if menu.css("a.cat-menu-item__link") and (menu.css("a.cat-menu-item__link").attrib["href"] not in [r"/Bizuteria_i_zegarki", r"/Moda", r"/Erotyka"])]

        # Get links to all sub-categories
        category_links = [menu.css(".pop-cat-item::attr(href)").getall() for menu in sub_menus if menu.css(".pop-cat-item")]

        # join list of lists
        category_links = list(chain.from_iterable(category_links))

        for i in range(0, len(category_links)):
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
                   
                    # Extract offer_ref from link.
                    link_ref_match = match("/[0-9]+", offer_link)
                    offer_ref = offer_link[link_ref_match.span()[0]+1:link_ref_match.span()[1]]

                    # If offer_ref wasn't found in previous scrapes then open offer site.
                    if offer_ref not in self.offer_refs: 

                        offer_link = r"https://www.ceneo.pl/" + offer_ref + ";0162-0"
                        self.offer_refs.add(offer_ref)

                        yield response.follow(offer_link, callback=self.parse_offer)

            except KeyError:
                # KeyError means offers with 0 reviews were found.
                passed_counter += 1

        # Go to a next page in the same category.
        # If Almost all offers have NO REVIEWS (High passed_counter) stop goind to the next pages.
        next_page = response.css("a.pagination__item.pagination__next")
        if next_page and (passed_counter < 27):
            yield response.follow(self.start_urls[0] + next_page.attrib["href"], callback=self.parse_category)

    def parse_offer(self, response):
        """
        Third Parsing Functions. Decides whether enough negative offers are found and follows up to a last scraping function.
        """
        
        # Get counts of all reviews, by their scores. 2 of these counters exist in website, so take only half of values.
        score_percents = response.css("div.js_score-popup-filter-link.score-extend__row")
        score_percents = score_percents[:len(score_percents)//2]

        # Get those values into a dict, divide by 100 to get actual percentage.
        score_dict = {int(score.css("span.score-extend__number::text").get()):  # Score number
                      float(score.css("span.score-extend__percent::text").get()[:-1])/100  # Percent of all Reviews
                      for score in score_percents}

        # Determine whether to scrape reviews with medium score.
        medium = True if score_dict[3] + score_dict[4] > 0 else False

        # If percentage of negative values is greater than 0 then follow up and scrape reviews.
        if score_dict[2] + score_dict[1] > 0:

            product_title = response.css("div.product-top__title h1::text").get()

            full_product_category = (response
                                        .css("nav.js_breadcrumbs.breadcrumbs")
                                        .css("a.js_breadcrumbs__item.breadcrumbs__item.link span::text")
                                        .getall())

            top_product_category = full_product_category[-1]

            full_product_category = "/".join(full_product_category[1:])

            reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
            
            # TODO get it into a serializer
            url_match = search("/[0-9]{2,}", response.request.url)
            current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]]
            
            negatives_scraped = 0

            for review in reviews:
                
                # Extract and Format score given by each reviewer. Stop scraping if review has ambiguous score (3)
                current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
                score_match = search("[0-9\.,]+/", current_score)
                current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
                current_score = float(current_score)


                if ((current_score <= 2) 
                    and (review.attrib["data-entry-id"] not in self.entry_ids)):

                    offer_data = CeneoscrapeItem()

                    # Add Review-Specific Data
                    # Offer refname
                    offer_data["offer_ref"] = current_offer_refname
                
                    # Entry ID
                    offer_data["entry_id"] = review.attrib["data-entry-id"]
                
                    # Review Text
                    offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0]
                                                               .css("div.user-post__text::text")
                                                               .getall())

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

            next_page = response.css("a.pagination__item.pagination__next")

            if (negatives_scraped == 10) and (len(next_page) > 0):
                
                # Continue scraping negative reviews on the next page.
                neg = partial(self.parse_review, positive=False, scraped_this_mode=10, medium=medium)

                yield response.follow(self.start_urls[0] + next_page.attrib["href"], callback=neg)

            else:

                # When negative cases have finished. Start scraping positive reviews.
                pos = partial(self.parse_review, positive=True, limit = negatives_scraped + 2, all_negatives_scraped = negatives_scraped + 2, medium=medium)
            
                if medium:
                    next_page = sub("(opinie-[0-9]+)*;0162-0", ";0162-0;ocena-4", str(response.request.url))

                else:
                    next_page = sub("(opinie-[0-9]+)*;0162-0", ";0162-1", str(response.request.url))

                yield response.follow(next_page, callback=pos)
            

    def parse_review(self, response, positive=False, limit = None, scraped_this_mode = 0, medium=False, all_negatives_scraped=0):
        
        # Get offer-specific item features: title/categories

        product_title = response.css("div.product-top__title h1::text").get()

        full_product_category = (response
                                 .css("nav.js_breadcrumbs.breadcrumbs")
                                 .css("a.js_breadcrumbs__item.breadcrumbs__item.link span::text")
                                 .getall())

        top_product_category = full_product_category[-1]

        full_product_category = "/".join(full_product_category[1:])

        reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
        
        # TODO get it into a serializer
        url_match = search("/[0-9]{2,}", response.request.url)
        current_offer_refname = response.request.url[url_match.span()[0]+1:url_match.span()[1]]
        
        scraped_this_round = 0

        for review in reviews[:limit]:
            
            # Extract and Format score given by each reviewer. Stop scraping if review has ambiguous score (3)
            current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
            score_match = search("[0-9\.,]+/", current_score)
            current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
            current_score = float(current_score)


            if (((positive and medium and (current_score < 4 and current_score > 2)) or
                (positive and not medium and current_score >= 4) 
                or (not positive and current_score <= 2)) 
                and (review.attrib["data-entry-id"] not in self.entry_ids)):

                offer_data = CeneoscrapeItem()

                # Add Review-Specific Data
                # Offer refname
                offer_data["offer_ref"] = current_offer_refname
            
                # Entry ID
                offer_data["entry_id"] = review.attrib["data-entry-id"]
            
                # Review Text
                offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0]
                                                           .css("div.user-post__text::text")
                                                           .getall())

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
                
                scraped_this_round += 1
                yield offer_data
        
        # Limit is a total of negative reviews scraped. 
        # Decrease the limit before going to a next page.
        if positive:
            limit -= scraped_this_round

        if positive and medium and (scraped_this_round < 10) and ("ocena-4" in str(response.request.url)):
            next_page = sub("(opinie-[0-9]+)*;0162-0;ocena-4", ";0162-1;ocena-3", str(response.request.url)[:len(self.start_urls[0])])

        elif scraped_this_round == 10:
            next_page = response.css("a.pagination__item.pagination__next")
            if len(next_page) > 0:
                next_page = next_page.attrib["href"]
        else:
            next_page = ""

        if (len(next_page) > 0) and positive and medium and (limit > 0) and ("ocena-4" in str(response.request.url)):
            
            # Continue Scraping medium score reviews on the next page.
            pos = partial(self.parse_review, positive=True, limit = limit, all_negatives_scraped=all_negatives_scraped, medium=True)
        
            yield response.follow(self.start_urls[0] + next_page, callback=pos)                        

        elif (len(next_page) > 0) and positive and (limit > 0) and (scraped_this_round == 10):
            
            # Continue Scraping positive reviews on the next page.
            pos = partial(self.parse_review, positive=True, limit = limit, all_negatives_scraped=all_negatives_scraped)
        
            yield response.follow(self.start_urls[0] + next_page, callback=pos)                        

        elif (len(next_page) > 0) and (not positive) and (scraped_this_round == 10):
            
            # Continue scraping negative reviews on the next page.
            neg = partial(self.parse_review, positive=False, scraped_this_mode=scraped_this_mode+scraped_this_round)

            yield response.follow(self.start_urls[0] + next_page, callback=neg)

        elif (not positive) and medium:
            
            # When negative cases have finished. Start scraping positive reviews.
            pos = partial(self.parse_review, positive=True, limit = scraped_this_mode + scraped_this_round + 2, medium=True, all_negatives_scraped=scraped_this_mode + scraped_this_round + 2)
        
            yield response.follow(sub("(opinie-[0-9]+)*;0162-0", ";0162-0;ocena-4", str(response.request.url)), callback=pos)
        
        elif (not positive):
    
            # When negative cases have finished. Start scraping positive reviews.
            pos = partial(self.parse_review, positive=True, limit = scraped_this_mode + scraped_this_round + 2)
        
            yield response.follow(sub("(opinie-[0-9]+)*;0162-0", ";0162-1", str(response.request.url)), callback=pos)
        
        elif (positive and medium):

            # When negative cases have finished. Start scraping positive reviews.
            pos = partial(self.parse_review, positive=True, limit = all_negatives_scraped)

            yield response.follow(sub("(opinie-[0-9]+)*;0162-1.*", ";0162-1", str(response.request.url)), callback=pos)

        else:
            pass
