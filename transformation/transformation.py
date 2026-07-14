import pandas as pd
import re 
import html 


INPUT_CSV = "../data/processed/dau_with_description.csv"
OUTPUT_CSV = "../data/processed/clean_description.csv"

def load_data(INPUT_CSV):
    """Load the input CSV into a pandas DataFrame.
    Args:
        INPUT_CSV (str): Path to the CSV file to read.
    Returns:
        pandas.DataFrame: The loaded data frame.
    """
    print(f"Loading data from {INPUT_CSV}")
    return pd.read_csv(INPUT_CSV, encoding="latin-1", low_memory=False)

def clean_description(text):
    """Clean HTML and entities from a description string.
    Converts HTML entities to text, strips tags and normalizes whitespace.
    Removes literal empty-quote placeholders (""), control characters, URLs
    and other non-human-readable noise. Returns None for missing or
    non-readable values.
    Args:
        text (str|None): Raw description text.
    Returns:
        str|None: Cleaned description or None.
    """
    if not text or pd.isna(text):
        return None

    text = str(text)

    # remove literal empty-quote placeholders like ""
    text = text.replace('""', '')

    # unescape HTML entities and remove tags
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)

    # remove URLs
    text = re.sub(r"http\S+|www\.[^\s]+", " ", text)

    # remove control / non-printable characters
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", text)

    # remove excessive non-alphanumeric clusters (likely noise)
    cleaned_chars = re.sub(r"\s+", "", re.sub(r"[A-Za-z0-9]", "", text))
    total_chars = len(re.sub(r"\s+", "", text))
    if total_chars > 0 and len(cleaned_chars) / total_chars > 0.6:
        return None

    # keep only common readable characters and normalize spaces
    text = re.sub(r"[^A-Za-z0-9\s\.,;:!\?\-\'\"]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    cleaned = text.strip()
    return cleaned if cleaned else None


def clean_author(author):
    """Normalize author names to lowercase and remove noise.
    This strips punctuation, bracketed content, digits and leaves only
    lowercase letters and spaces.
    Args:
        author (str|None): Raw author string.
    Returns:
        str|None: Normalized author or None for missing values.
    """
    if not author or pd.isna(author):
        return None

    author = str(author).lower()
    # remove unwanted punctuation
    author = re.sub(r"[.,/]", " ", author)
    # remove brackets content
    author = re.sub(r"\(.*?\)", "", author)
    # remove numbers
    author = re.sub(r"\d+", "", author)
    # keep letters and spaces only
    author = re.sub(r"[^a-z ]", " ", author)
    # normalize spaces
    author = re.sub(r"\s+", " ", author)

    return author.strip()

## Formatting the column Names

def Format_col(df):
    """Standardize column names to the project's schema.
    Args:
        df (pandas.DataFrame): Input DataFrame.
    Returns:
        pandas.DataFrame: DataFrame with renamed columns.
    """
    description_d = ['ISBN Not Matched' , 'Description Not Available' , "Not Found"]

    df['description'] = df['description'].replace(description_d,"Not Found")

    return df
    
## Drop Description Not Found Rows
def drop_rows(df):
    # 1. Get the indices of the rows to remove
    indices_to_drop = df[df['description'] == "Not Found"].index
    df.drop(indices_to_drop , inplace=True)
    return df

def pad_isbn(isbn):
    """Pad ISBN to length 10 with leading zeros if shorter.
    Removes non-digit characters and returns None for missing/invalid values.
    Args:
        isbn (str|int|None): Raw ISBN value.
    Returns:
        str|None: Normalized 10-digit ISBN or None.
    """
    if pd.isna(isbn):
        return None
    s = str(isbn).strip()
    # keep only digits and X/x
    s = re.sub(r"[^0-9Xx]", "", s)
    if not s:
        return None

    # If X/x appears anywhere except the last position -> invalid
    if any(ch in "Xx" for ch in s[:-1]):
        return None
    if len(s) == 9:
        if s != ["X","x"]:
            s = s.zfill(10)
        print(s)
    return s


def handle_ISBN(df):
    """Apply pad_isbn and drop rows with invalid ISBNs."""
    before = df.shape[0]
    df['ISBN'] = df['ISBN'].apply(pad_isbn)
    df = df[df['ISBN'].notna() & (df['ISBN'] != '')].copy()
    after = df.shape[0]
    dropped = before - after
    if dropped:
        print(f"Dropped {dropped} rows due to invalid ISBNs ⚠️")
    return df


def transformation():
    """Run the transformation steps and write the output CSV.
    This function loads the processed CSV, cleans descriptions and author
    names, drops unwanted columns, standardizes column names, and writes
    the transformed data to `OUTPUT_CSV`.
    """
    df = load_data(INPUT_CSV)
    df['description'] = df['description'].apply(clean_description)
    df["Author_Editor"] = df["Author_Editor"].apply(clean_author)
    df = Format_col(df)
    df = handle_ISBN(df)

    df.to_csv(OUTPUT_CSV, index=False)
    print("Transformation completed successfully")
    print(f"Rows before: {df.shape[0]}")
    # ... apply drop logic ...
    print(f"Rows after: {df.shape[0]}")
 
if __name__ == "__main__":
    transformation()