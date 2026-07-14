import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote_plus

INPUT_CSV = "../data/rae/RC_books.csv"
FINAL_OUTPUT = "../data/processed/dau_with_description.csv"

MISSING_VALUES = ["Not Found", "ISBN Not Matched", "Description Not Available"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Sahil-BookBot/1.0)"
}

import logging
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)



def clean_isbn(isbn):
    return re.sub(r"[^0-9Xx]", "", str(isbn))


def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def load_library_data():
    columns = [
        "Acc_Date", "Acc_No", "Title", "ISBN", "Author_Editor",
        "Edition_Volume", "Place_Publisher", "Year", "Pages", "Class_No"
    ]
    df = pd.read_csv(
        INPUT_CSV,
        usecols=range(len(columns)),
        names=columns,
        header=0,
        dtype={"ISBN": str},
        encoding="latin1"
    )
    df = df.drop_duplicates(subset=["ISBN"])
    df["description"] = "Not Found"
    return df

## Session Creation
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def make_session(max_workers=50):
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(
        pool_connections=max_workers,
        pool_maxsize=max_workers,
        max_retries=retry
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session



from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


## Open Library logic
def fetch_openlibrary_json_descriptions(df, max_workers=20, delay=0.05):
    df = df.copy()
    df["description"] = "ISBN Not Matched"

    lock = threading.Lock()
    session = make_session(max_workers=max_workers)

    def fetch_description(row_index, isbn):
        desc = "ISBN Not Matched"
        isbn_clean = clean_isbn(isbn)

        if not isbn_clean:
            with lock:
                df.at[row_index, "description"] = desc
            return

        try:
            url = f"https://openlibrary.org/isbn/{isbn_clean}.json"
            r = session.get(url, headers=HEADERS, timeout=10)

            if r.status_code != 200:
                desc = "Not Found"
            else:
                data = r.json()

                # description
                if "description" in data:
                    if isinstance(data["description"], dict):
                        desc = data["description"].get("value", "")
                    else:
                        desc = data["description"]

                # fallback: first_sentence
                if (not desc) and ("first_sentence" in data):
                    if isinstance(data["first_sentence"], dict):
                        desc = data["first_sentence"].get("value", "")
                    else:
                        desc = data["first_sentence"]

                # Works endpoint fallback
                if (not desc) and ("works" in data) and len(data["works"]) > 0:
                    work_key = data["works"][0].get("key")
                    if work_key:
                        work_url = f"https://openlibrary.org{work_key}.json"
                        w = session.get(work_url, headers=HEADERS, timeout=10)
                        if w.status_code == 200:
                            wdata = w.json()
                            if "description" in wdata:
                                if isinstance(wdata["description"], dict):
                                    desc = wdata["description"].get("value", "")
                                else:
                                    desc = wdata["description"]

                if not desc:
                    desc = "Description Not Available"

        except:
            desc = "Not Found"

        time.sleep(delay)
        with lock:
            df.at[row_index, "description"] = desc

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, row in df.iterrows():
            futures.append(executor.submit(fetch_description, i, row["ISBN"]))

        for _ in tqdm(as_completed(futures), total=len(futures), desc="OpenLibrary JSON"):
            pass

    session.close()
    return df

## Google Logic
def fetch_google_html_descriptions(df, max_workers=20, delay=0.05):
    df = df.copy()
    lock = threading.Lock()

    session = make_session(max_workers=max_workers)

    def fetch_description(row_index, isbn):
        desc = df.at[row_index, "description"]
        isbn_clean = clean_isbn(isbn)

        if desc not in MISSING_VALUES:
            return

        if isbn_clean:
            try:
                url = f"https://books.google.com/books?vid=ISBN{isbn_clean}"
                r = session.get(url, headers=HEADERS, timeout=10)
                soup = BeautifulSoup(r.text, "html.parser")

                div = soup.find("div", class_="Mhmsgc") or soup.find("div", id="synopsistext")
                if div:
                    desc = div.get_text(separator=" ", strip=True)

            except:
                pass

        time.sleep(delay)
        with lock:
            df.at[row_index, "description"] = desc

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, row in df.iterrows():
            if df.at[i, "description"] in MISSING_VALUES:
                futures.append(executor.submit(fetch_description, i, row["ISBN"]))

        for _ in tqdm(as_completed(futures), total=len(futures), desc="Google HTML"):
            pass

    session.close()
    return df


def fetch_bookswagon_descriptions(df, max_workers=10, delay=0.1):
    df = df.copy()
    lock = threading.Lock()

    session = make_session(max_workers=max_workers)

    def fetch_description(row_index, isbn):
        desc = df.at[row_index, "description"]
        isbn_clean = clean_isbn(isbn)

        if desc not in MISSING_VALUES:
            return

        if not isbn_clean:
            return

        # Bookswagon prefers ISBN13 in URL
        # If ISBN is 10-digit, try to still use it (some works, some not)
        try:
            url = f"https://www.bookswagon.com/book/c/{isbn_clean}"
            r = session.get(url, headers=HEADERS, timeout=10)

            soup = BeautifulSoup(r.text, "html.parser")

            # Main about book section
            about_div = soup.find("div", id="aboutbook")
            if about_div:
                p = about_div.find("p")
                if p:
                    text = p.get_text(separator=" ", strip=True)
                    if text and len(text) > 30:
                        desc = text

        except:
            pass

        time.sleep(delay)
        with lock:
            df.at[row_index, "description"] = desc

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, row in df.iterrows():
            if df.at[i, "description"] in MISSING_VALUES:
                futures.append(executor.submit(fetch_description, i, row["ISBN"]))

        for _ in tqdm(as_completed(futures), total=len(futures), desc="Bookswagon"):
            pass

    session.close()
    return df


def fetch_google_api_fallback(df, max_workers=20, delay=0.05):
    df = df.copy()

    df["clean_title"] = df["Title"].apply(clean_text)
    df["clean_author"] = df["Author_Editor"].apply(clean_text)

    lock = threading.Lock()
    session = make_session(max_workers=max_workers)

    def fetch_description(row_index, clean_title, clean_author):
        desc = df.at[row_index, "description"]

        if desc not in MISSING_VALUES:
            return

        queries = [
            f"intitle:{clean_title}+inauthor:{clean_author}",
            f"intitle:{clean_title}"
        ]

        for q in queries:
            try:
                url = f"https://www.googleapis.com/books/v1/volumes?q={quote_plus(q)}&maxResults=1"
                res = session.get(url, timeout=10).json()

                items = res.get("items")
                if not items:
                    continue

                result = items[0].get("volumeInfo", {}).get("description")
                if result and len(result) > 30:
                    desc = result
                    break
            except:
                pass

        time.sleep(delay)
        with lock:
            df.at[row_index, "description"] = desc

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, row in df.iterrows():
            if row["description"] in MISSING_VALUES:
                futures.append(executor.submit(
                    fetch_description,
                    i,
                    row["clean_title"],
                    row["clean_author"]
                ))

        for _ in tqdm(as_completed(futures), total=len(futures), desc="Google API"):
            pass

    session.close()
    return df.drop(columns=["clean_title", "clean_author"])


def copy_isbn(df1, df4):
    df_lib = df1.copy()
    df_desc = df4.copy()

    match_cols = ["Title", "Author_Editor", "Edition_Volume", "Place_Publisher", "Year"]

    def clean_text_for_match(text):
        text = str(text).lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    for col in match_cols:
        df_lib[col + "_clean"] = df_lib[col].apply(clean_text_for_match)
        df_desc[col + "_clean"] = df_desc[col].apply(clean_text_for_match)

    isbn_map = df_lib.set_index([col + "_clean" for col in match_cols])["ISBN"].to_dict()

    def get_isbn(row):
        key = tuple(row[col + "_clean"] for col in match_cols)
        return isbn_map.get(key, row["ISBN"])

    df_desc["ISBN"] = df_desc.apply(get_isbn, axis=1)

    df_desc.drop(columns=[col + "_clean" for col in match_cols], inplace=True)

    return df_desc


def run_pipeline():
    print("Loading base library data...")
    df1 = load_library_data()

    print("Fetching OpenLibrary JSON descriptions...")
    df2 = fetch_openlibrary_json_descriptions(df1)

    print("Fetching Google Books HTML descriptions...")
    df3 = fetch_google_html_descriptions(df2)

    print("Fetching Bookswagon fallback descriptions...")
    df4 = fetch_bookswagon_descriptions(df3)

    print("Fetching Google Books API fallback descriptions...")
    df5 = fetch_google_api_fallback(df4)

    print("Copy ISBN...")
    df6 = copy_isbn(df1, df5)

    print("Saving FINAL output...")
    df6.to_csv(FINAL_OUTPUT, index=False)

    print(f"\n✅ DONE Final file created: {FINAL_OUTPUT}")


if __name__ == "__main__":
    run_pipeline()