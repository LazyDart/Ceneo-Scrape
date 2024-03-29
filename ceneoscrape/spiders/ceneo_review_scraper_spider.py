import scrapy

from functools import partial
from ceneoscrape.items import CeneoscrapeItem

import os
import csv

from re import sub, match, search
from random import shuffle
from itertools import chain

class CeneoReviewScraperSpider(scrapy.Spider):

    def __init__(self, fill_holes=False, positive_increase="3", *args, **kwargs):
        super(CeneoReviewScraperSpider, self).__init__(*args, **kwargs)
        self.fill_holes = bool(fill_holes)
        self.positive_increase = int(positive_increase)
        self.offer_refs = set()
        self.entry_ids = set()    


    name = "ceneocatselect"
    allowed_domains = ["www.ceneo.pl"]
    start_urls = ["https://www.ceneo.pl/"]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 3000,
                    #    'CLOSESPIDER_ITEMCOUNT': 4000, 
                       'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
                       'DOWNLOAD_DELAY': .5}

    
    # Set current dir as part of Path to easly locate "output.csv" or "supplement.csv"
    os.chdir(os.path.dirname(__file__))
    

    def start_requests(self):

        # After Initialization Load all previously saved data id's
        # This will assure no duplicates are generated 
        # and no site will needlessly load.
        if self.fill_holes:
            # supplement.csv is hard coded, this is a default output name for my program
            # In case of filling holes after errors of default parsing methods.
            # If it is found, offer_refs and entry_ids are populated with data.
            if "supplement.csv" in os.listdir("./"):
                
                # Data is Read using csv library.
                file = open("supplement.csv")
                olderdata = csv.reader(file)
                for row in olderdata:
                    self.entry_ids.add(row[1]) # Limits duplicate reviews
                
                file.close()
            
            yield scrapy.Request(url=self.start_urls[0], callback=self.start_fill_hole_parsing)
        
        else:
            # output.csv is hard coded, this is a default output name for my programm.
            # If it is found, offer_refs and entry_ids are populated with data.
            if "output.csv" in os.listdir("./"):
                
                # Data is Read using csv library.
                file = open("output.csv")
                olderdata = csv.reader(file)
                for row in olderdata:
                    self.entry_ids.add(row[1])  # limits duplicate reviews
                    self.offer_refs.add(row[3])  # limits duplcate requests
                
                file.close()

            yield scrapy.Request(url=self.start_urls[0], callback=self.start_default_parsing)


    def start_default_parsing(self, response):
        """
        First Parsing Function

        Loads Ceneo Home-page and reads "most popular categories" link.
        Then opens link to each of those categories.
        TODO: Maybe an option exists to browse all categories. Not only popular ones.
        """
        
        # Get All categories sub menus
        sub_menus = response.css("div.js_cat-menu-item.cat-menu-item")
        
        # For each menu excluding jewelry, fashion and erotic get all sub-categories
        sub_menus = [menu for menu in sub_menus 
                     if menu.css("a.cat-menu-item__link") 
                        and (menu.css("a.cat-menu-item__link").attrib["href"] not in [r"/Bizuteria_i_zegarki",
                                                                                      r"/Moda",
                                                                                      r"/Erotyka"])
        ]

        # Get links to all sub-categories
        category_links = [menu.css(".pop-cat-item::attr(href)").getall() for menu in sub_menus if menu.css(".pop-cat-item")]

        # join list of lists
        category_links = list(chain.from_iterable(category_links))

        shuffle(category_links)

        # for i in range(0, len(category_links)):
        for category_link in category_links: 

            # Get full link to a page by concatenating starting url with single category_link. 
            current_category = self.start_urls[0] + category_link#category_links[i]

            # Follow to a Second Parsing Function.
            yield response.follow(current_category, callback=self.parse_category)

        pass

    def start_fill_hole_parsing(self, response):
        if "unfinished offers.csv" in os.listdir("./"):
            os.chdir(os.path.dirname(__file__))
            from .update_unfinished import main
            main()
            
            # Data is Read using csv library.
            file = open("unfinished offers.csv")
            olderdata = csv.reader(file)
            
            offer_batch = list(olderdata)[1:]
            shuffle(offer_batch)

            for row in offer_batch[:1000]:
                offer_link = self.start_urls[0] + row[0] + ";0162-0"
                partial_smaller_increase = partial(self.parse_offer)
                partial_smaller_increase.__name__ = "parse_offer"

                yield response.follow(offer_link, callback=partial_smaller_increase)

            # for row in offer_batch:
            #     offer_link = self.start_urls[0] + row[0] + "#tab=reviews_scroll"
            #     yield response.follow(offer_link, callback=self.extract_review_count)

            file.close()
    


    def extract_review_count(self, response):
        # Get counts of all reviews, by their scores. 2 of these counters exist in website, so take only half of values.
        score_percents = response.css("div.js_score-popup-filter-link.score-extend__row")
        score_percents = score_percents[:len(score_percents)//2]

        # Get those values into a dict, divide by 100 to get actual percentage.
        score_dict = {int(score.css("span.score-extend__number::text").get()):  # Score number
                      float(score.css("span.score-extend__percent::text").get()[:-1])/100  # Percent of all Reviews
                      for score in score_percents}
        
        offer_data = CeneoscrapeItem()
        offer_data["offer_ref"] = response.request.url
    
        offer_data["entry_id"] = score_dict[1] + score_dict[2]
        offer_data["review_text"] = score_dict[3]
        offer_data["score"] = score_dict[4] + score_dict[5]
        offer_data["entry_date"] = ""
        offer_data["purchase_date"] = ""
        offer_data["product_title"] = ""
        offer_data["full_category"] = ""
        offer_data["top_category"] = ""
            
        yield offer_data


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
                    and (r"https://redirect.ceneo.pl/offers/" not in offer_link)
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

        pagination_match = search("-\d-\d-\d{,2}", response.request.url)

        # Calculate how many pages in current category were scraped.
        if pagination_match:
            page_number = int(response.request.url[pagination_match.span()[0]: pagination_match.span()[1]].split("-")[-1])
        else:
            page_number=0

        # If enough items are valid, next page exists and pagination does not exceed 5 pages limit.
        if next_page and (passed_counter < 27) and (page_number < 5):
            # Go to next page.
            yield response.follow(self.start_urls[0] + next_page.attrib["href"], callback=self.parse_category)


    def scrape_reviews(self, response, positive, neutral, limit):
        """
        Function collects all reviews from a single page. Counts them. and returns as a list of items.

        Arguments define what type of reviews to scrape.
        """
        # Get offer-specific item features: title/categories

        product_title = response.css("div.product-top__title h1::text").get()

        full_product_category = (response
                                 .css("nav.js_breadcrumbs.breadcrumbs")
                                 .css("a.js_breadcrumbs__item.breadcrumbs__item.link span::text")
                                 .getall())

        top_product_category = full_product_category[-1]

        full_product_category = "/".join(full_product_category[1:])

        reviews = response.css("div.user-post.user-post__card.js_product-review")[:10]
        
        scraped_this_round = 0

        items_list = []

        for review in reviews[:limit]:
            
            # Extract and Format score given by each reviewer. Stop scraping if review has ambiguous score (3)
            current_score = review.css("div.user-post__content")[0].css("span.user-post__score-count::text").get()
            score_match = search("[0-9\.,]+/", current_score)
            current_score = sub(",", ".", current_score[score_match.span()[0]:score_match.span()[1]-1])
            current_score = float(current_score)
            
            # Only include reviews with score adequate to the type of review. Exclude duplicates.
            if (((positive and neutral and (current_score < 4 and current_score > 2)) or
                (positive and not neutral and current_score >= 4) 
                or (not positive and current_score <= 2))):

                if review.attrib["data-entry-id"] not in self.entry_ids:

                    offer_data = CeneoscrapeItem()

                    # Add Review-Specific Data
                    # Offer refname
                    offer_data["offer_ref"] = response.request.url
                
                    # Entry ID
                    offer_data["entry_id"] = review.attrib["data-entry-id"]
                    self.entry_ids.add(review.attrib["data-entry-id"])


                    # Review Text
                    offer_data["review_text"] = " ".join(review.css("div.user-post__content")[0]
                                                            .css("div.user-post__text::text")
                                                            .getall())

                    # Score
                    offer_data["score"] = current_score

                    # Extract Dates
                    datetimes = reviews.css("div.user-post__content span.user-post__published time")

                    offer_data["entry_date"] = datetimes[0].attrib["datetime"]
                    if len(datetimes) > 1:
                        offer_data["purchase_date"] = datetimes[1].attrib["datetime"]
                    else:
                        offer_data["purchase_date"] = ""

                    # Add offer specific data.
                    offer_data["product_title"] = product_title
                    offer_data["full_category"] = full_product_category
                    offer_data["top_category"] = top_product_category
                    
                    scraped_this_round += 1
                    items_list.append(offer_data)

                else:
                    scraped_this_round += 1

        return items_list, scraped_this_round


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

        # Determine whether to scrape reviews with neutral score.
        neutral = True if score_dict[3] + score_dict[4] > 0 else False

        # If percentage of negative values is greater than 0 then follow up and scrape reviews.
        if score_dict[2] + score_dict[1] > 0:
            
            # Scrape all reviews from current page.
            items_list, negatives_scraped = self.scrape_reviews(response, False, False, 11)

            # Save all items scraped from scrape_reviews function.
            for item in items_list:
                yield item

            # Get next page of offer reviews.
            next_page = response.css("a.pagination__item.pagination__next")
            
            # If negative reviews continue on next page.
            if (negatives_scraped == 10) and (len(next_page) > 0):
                
                # Continue scraping negative reviews on the next page.
                neg = partial(self.parse_reviews_page, 
                              positive=False, 
                              scraped_this_mode=10, 
                              neutral=neutral, 
                              review_percentage=score_dict,
                              )
                neg.__name__ = "parse_reviews_page"

                yield response.follow(self.start_urls[0] + next_page.attrib["href"], callback=neg)

            else:
                
                # When negative cases have finished. Start scraping positive reviews.
                pos = partial(self.parse_reviews_page, 
                              positive=True, 
                              limit = negatives_scraped + self.positive_increase, 
                              all_negatives_scraped = negatives_scraped + self.positive_increase, 
                              neutral=neutral, 
                              review_percentage=score_dict,
                              )
                pos.__name__ = "parse_reviews_page"

                if neutral and (score_dict[4] > 0):
                    next_page = sub("(opinie-[0-9]+)*;0162-0", ";0162-0;ocena-4", str(response.request.url))
                
                elif neutral and (score_dict[4] > 0):
                    next_page = sub("(opinie-[0-9]+)*;0162-0", ";0162-1;ocena-3", str(response.request.url))

                else:
                    next_page = sub("(opinie-[0-9]+)*;0162-0", ";0162-1", str(response.request.url))

                yield response.follow(next_page, callback=pos)
        else:
            # This saves offer data even if no reviews were found.
            # For later runs this offer will be ignored.
            offer_data = CeneoscrapeItem()
            offer_data["offer_ref"] = response.request.url
        
            offer_data["entry_id"] = ""
            offer_data["review_text"] = ""
            offer_data["score"] = ""
            offer_data["entry_date"] = ""
            offer_data["purchase_date"] = ""
            offer_data["product_title"] = ""
            offer_data["full_category"] = ""
            offer_data["top_category"] = ""
            
            yield offer_data
            


    def parse_reviews_page(self, 
                     response, 
                     positive=False, 
                     limit = None, 
                     scraped_this_mode = 0, 
                     neutral=False, 
                     all_negatives_scraped=0, 
                     review_percentage=None):
        """
        Fourth Parsing Function. Scrapes reviews from a single page. 
        Then decides whether to continue scraping and what type of reviews to look for next.

        Arguments pass the state of scraping current offer to help decide where to move next.
        """


        # Scrape all reviews from current page.
        items_list, scraped_this_round = self.scrape_reviews(response, positive, neutral, limit)

        for item in items_list:
            yield item
        
        # Limit is a total of negative reviews scraped. 
        # Decrease the limit before going to a next page.
        if positive:
            limit -= scraped_this_round
        
        # Determine what is the next page to scrape.
        if (positive and neutral and (scraped_this_round < 10) 
            and ("ocena-4" in str(response.request.url)) and (review_percentage[3] > 0)):
            # Reviews with score 4 turn to score 3.
            next_page = sub("(opinie-[0-9]+)*;0162-0;ocena-4", 
                            ";0162-1;ocena-3", 
                            str(response.request.url)[len(self.start_urls[0]):])

        elif scraped_this_round == 10:
            # continue with the same mode of scraping.
            next_page = response.css("a.pagination__item.pagination__next")
            if len(next_page) > 0:
                next_page = next_page.attrib["href"]
        else:
            # No Next page exists. stop scraping or change mode.
            next_page = ""


        if ((len(next_page) > 0) and positive and neutral and (limit > 0)  
             and ("ocena-4" in str(response.request.url)) and (review_percentage[3] > 0)):
            
            # Continue Scraping neutral score reviews on the next page.
            pos = partial(self.parse_reviews_page, 
                          positive = True, 
                          limit = limit, 
                          scraped_this_mode = scraped_this_mode + scraped_this_round,
                          all_negatives_scraped = all_negatives_scraped, 
                          neutral = True,
                          review_percentage = review_percentage)
            pos.__name__ = "parse_reviews_page"
        
            yield response.follow(self.start_urls[0] + next_page, callback=pos)                        

        elif (len(next_page) > 0) and positive and (limit > 0) and (scraped_this_round == 10):
            
            # Continue Scraping positive reviews on the next page.
            pos = partial(self.parse_reviews_page, 
                          positive=True, 
                          limit = limit,
                          scraped_this_mode = scraped_this_mode + scraped_this_round,
                          all_negatives_scraped = all_negatives_scraped, 
                          review_percentage = review_percentage)
            pos.__name__ = "parse_reviews_page"
        
            yield response.follow(self.start_urls[0] + next_page, callback=pos)                        

        elif (len(next_page) > 0) and (not positive) and (scraped_this_round == 10):
            
            # Continue scraping negative reviews on the next page.
            neg = partial(self.parse_reviews_page, 
                          positive=False,
                          scraped_this_mode = scraped_this_mode + scraped_this_round, 
                          review_percentage = review_percentage)
            neg.__name__ = "parse_reviews_page"

            yield response.follow(self.start_urls[0] + next_page, callback=neg)

        elif (not positive) and neutral:
            
            # When negative cases have finished. Start scraping neutral reviews.
            pos = partial(self.parse_reviews_page, 
                          positive=True, 
                          limit = scraped_this_mode + scraped_this_round + self.positive_increase, 
                          neutral = True, 
                          all_negatives_scraped = scraped_this_mode + scraped_this_round + self.positive_increase, 
                          review_percentage = review_percentage)
            pos.__name__ = "parse_reviews_page"

            next_review_type = ";0162-0;ocena-4" if review_percentage[4] > 0 else ";0162-1;ocena-3"

            yield response.follow(sub("(opinie-[0-9]+)*;0162-0", 
                                      next_review_type, 
                                      str(response.request.url)),
                                  callback = pos)
        
        elif (not positive):
    
            # When negative cases have finished. Start scraping positive reviews.
            pos = partial(self.parse_reviews_page, 
                          positive=True, 
                          limit = scraped_this_mode + scraped_this_round + self.positive_increase,
                          all_negatives_scraped = scraped_this_mode + scraped_this_round + self.positive_increase,
                          review_percentage = review_percentage)
            
            pos.__name__ = "parse_reviews_page"
        
            yield response.follow(sub("(opinie-[0-9]+)*;0162-0", 
                                      ";0162-1", 
                                      str(response.request.url)),
                                  callback=pos)
        
        elif (positive and neutral):

            # When neutral cases have finished. Start scraping positive reviews.
            pos = partial(self.parse_reviews_page, 
                          positive=True,
                          limit = all_negatives_scraped,
                          all_negatives_scraped = all_negatives_scraped,
                          review_percentage = review_percentage)
            
            pos.__name__ = "parse_reviews_page"


            yield response.follow(sub("(opinie-[0-9]+)*;0162-[0-1].*", 
                                      ";0162-1", 
                                      str(response.request.url)), 
                                 callback=pos)

        else:
            pass
