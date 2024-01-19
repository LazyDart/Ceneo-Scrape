import os
import pandas as pd

def main(new_scrape_file="supplement.csv", unfinished_file="unfinished offers.csv"):
    
    # Cleaning newly scaped data
    df = pd.read_csv(new_scrape_file)
    df["score"] = pd.to_numeric(df["score"], errors='coerce')
    df = df.dropna(subset=["score"])
    df = df.drop_duplicates(subset=["offer_ref", "entry_id", "review_text"])

    # Get positive and negative reviews for each offer
    comparison = pd.merge(df[df["score"] <= 2].groupby("offer_ref")["review_text"].count(), 
                          df[df["score"] >= 4].groupby("offer_ref")["review_text"].count(), how="outer", on="offer_ref")

    # Get those that have more positive than negative reviews
    finished = comparison[(comparison["review_text_x"] <= comparison["review_text_y"]) & (~comparison["review_text_y"].isna())].index.to_series()

    # read unfinished offers
    unfinished = pd.read_csv(unfinished_file)

    # Remove finished offers from unfinished file and save it.
    unfinished[~unfinished["offer_ref"].isin(finished.astype(int))].to_csv(unfinished_file, index=False)

    pass

if __name__ == "__main__":
    newly_scraped = input("Please provide the name of the newly scraped file (default: supplement.csv): ")
    unfinished = input("Please provide the name of the unfinished offers file (default: unfinished offers.csv): ")

    newly_scraped = newly_scraped if newly_scraped else "supplement.csv"
    unfinished = unfinished if unfinished else "unfinished offers.csv"

    os.chdir(os.path.dirname(__file__))
    main(new_scrape_file=newly_scraped, unfinished_file=unfinished)


