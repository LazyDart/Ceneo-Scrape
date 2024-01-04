![Review Scraper Project](Ceneo_Review_Scraper.png)

This project is a web scraper implemented in Python using the Scrapy framework. It is designed to scrape reviews from the Ceneo website, while maintaining class balance between Positive, Negative and Neutral reviews. Scraper maintains roughly the same number of each classes throughout different categories of product.<br>
It is a first part of my Sentiment Analysis of Ceneo Reviews project. For the second part go to:<br>
https://github.com/LazyDart/Review-Sentiment-Analysis

## Key Features
1. Category Selection: The scraper navigates through the most popular categories on the Ceneo website.
2. Duplicate Prevention: Sets (`offer_refs` and `entry_ids`) are used to prevent duplicate entries and maintain data integrity.
3. Output Data Management: The scraper reads previously scraped data from the "output.csv" file, populating sets to avoid duplicates.
4. Custom Settings: Custom settings such as `CLOSESPIDER_PAGECOUNT` and `DOWNLOAD_DELAY` control spider behavior.
5. Multiple Parsing Functions: Three parsing functions (`parse`, `parse_category`, and `parse_offer`) handle different levels of the website.
6. Review Scraping: The scraper extracts reviews from product pages based on specific criteria, such as negative reviews with a score less than 5.
7. Pagination Handling: The scraper manages pagination within categories to ensure all relevant reviews are scraped.

## Usage

1. Install the required dependencies:
```sh    
bash
pip install itemadapter==0.8.0 Scrapy==2.11.0 pandas==2.0.0
```
2. Run the scraper:
```sh
bash
scrapy crawl ceneocatselect -o output.csv
```
Note: Use this command inside the project directory to ensure Scrapy detects the spider.

After cloning the repository locally and installing Scrapy, the scraper should work without additional steps.

## Additional Information
### Versions
    itemadapter==0.8.0
    Scrapy==2.11.0
    pandas==2.0.0

### Output Format
The output format is CSV, and users should write data to the "output.csv" file so the scraper can read it and include already scraped data in decision making.

### Limitations
Ceneo may block the scraper after 1.5 hours of work. To avoid this, the `CLOSESPIDER_PAGECOUNT: 3000` setting is recommended. Alternatively, implementing AutoCaptcha or proxy swapping can help avoid being blocked.

Feel free to reach out for any further clarifications or customization needs.