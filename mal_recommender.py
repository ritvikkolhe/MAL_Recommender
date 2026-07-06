"""
MyAnimeList Recommendation Analyzer

Features
--------
1. Downloads and analyzes a public MyAnimeList anime list
2. Uses configurable caching for user lists, top anime data,
   and anime metadata pages
3. Builds recommendations from the Top N most popular anime
   (default: Top 250)
4. Excludes Completed and Dropped anime from recommendations
5. Keeps Currently Watching, On Hold, and Planned anime visible
6. Filters recommendations using a configurable minimum score
7. Scrapes and caches additional anime metadata:
   - English title
   - Type
   - Episode count
   - Release year
   - Genres
8. Exports recommendations to CSV
9. Generates an interactive HTML report with:
   - Clickable MyAnimeList links
   - Sortable Rank, Score, and Year columns
   - Japanese / English title toggle
   - Highlighting for anime already on the user's list
10. Automatically opens the generated report

Outputs
-------
output/my_list.csv
output/recommendations.csv
output/recommendations.html

Cache
-----
cache/config.json
cache/my_list_<username>.json
cache/top_anime.csv
cache/anime_details/

Author:
    Ritvik Kolhe
"""

import json
import os
import re
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURATION
# ============================================================

TOP_PAGES = 5  # 5 pages x 50 entries = Top 250
CACHE_HOURS = 24
USERNAME = ""
MIN_SCORE = 8.0
HTML_ROWS = 30

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CONFIG_FILE = f"{CACHE_DIR}/config.json"

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DETAILS_CACHE_DIR = f"{CACHE_DIR}/anime_details"

os.makedirs(DETAILS_CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

DEFAULT_CONFIG = {
    "username": "",
    "top_pages": 5,
    "cache_hours": 24,
    "min_score": 8.0,
    "html_rows": 30,
}


def load_config():
    """
    Load settings from config.json.

    Creates the configuration file with default
    values if it does not already exist.

    Also ensures newly added configuration
    options are automatically populated.
    """

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)

        return DEFAULT_CONFIG

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    updated = False

    for key, value in DEFAULT_CONFIG.items():

        if key not in config:
            config[key] = value
            updated = True

    if updated:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    return config


# ============================================================
# STATUS MAPPINGS
# ============================================================

USER_STATUS_MAP = {
    1: "Currently Watching",
    2: "Completed",
    3: "On Hold",
    4: "Dropped",
    6: "Planned To Watch",
}

AIRING_STATUS_MAP = {
    1: "Currently Airing",
    2: "Released",
    3: "Not Released",
}


# ============================================================
# CACHE HELPERS
# ============================================================


def cache_is_valid(filepath):
    """
    Determine whether a cache file can be reused.

    Returns True when:
    - The file exists
    - The file is newer than CACHE_HOURS

    Otherwise, returns False.
    """

    if not os.path.exists(filepath):
        return False

    modified = datetime.fromtimestamp(os.path.getmtime(filepath))

    return datetime.now() - modified < timedelta(hours=CACHE_HOURS)


# ============================================================
# GENERAL HELPERS
# ============================================================


def get_anime_details(anime_id, anime_url):
    """
    Retrieve anime metadata from its MAL page.

    Data is cached locally to avoid repeated
    requests and improve performance.

    Metadata collected:
    - English title
    - Type
    - Episode count
    - Release year
    - Genres
    """

    cache_file = f"{DETAILS_CACHE_DIR}/{anime_id}.json"

    if cache_is_valid(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    try:

        print(f"Fetching anime details for {anime_url.split('/')[-1]}")

        response = requests.get(
            anime_url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        data = {
            "english_title": "",
            "type": "",
            "episodes": "",
            "year": "",
            "genres": "",
        }

        # English title

        english_span = soup.find(
            "span", class_="dark_text", string=re.compile(r"English:", re.I)
        )

        if english_span:
            data["english_title"] = (
                english_span.parent.get_text(" ", strip=True)
                .replace("English:", "")
                .strip()
            )

        # Type

        type_label = soup.find(string=re.compile(r"Type:", re.I))

        if type_label:
            node = type_label.parent
            link = node.find_next("a")

            if link:
                data["type"] = link.text.strip()

        # Episodes

        episodes_span = soup.find(
            lambda tag: tag.name == "span" and "Episodes:" in tag.get_text()
        )

        if episodes_span:
            data["episodes"] = (
                episodes_span.parent.get_text(" ", strip=True)
                .replace("Episodes:", "")
                .strip()
            )

        # Year

        aired_span = soup.find(
            lambda tag: tag.name == "span" and "Aired:" in tag.get_text()
        )

        if aired_span:

            text = aired_span.parent.get_text(" ", strip=True)

            year_match = re.search(r"(19|20)\d{2}", text)

            if year_match:
                data["year"] = year_match.group()

        # Genres

        genres = []

        for genre in soup.select('span[itemprop="genre"]'):
            genres.append(genre.text.strip())

        data["genres"] = ", ".join(genres)

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return data

    except Exception as e:

        print(f"Failed to fetch details " f"for anime {anime_id}: {e}")

        return {
            "english_title": "",
            "type": "",
            "episodes": "",
            "year": "",
            "genres": "",
        }


def extract_id(url):
    """
    Extract anime ID from MAL URL.
    Example:
        https://myanimelist.net/anime/5114/...
        -> 5114
    """

    match = re.search(r"/anime/(\d+)/", str(url))

    if match:
        return int(match.group(1))

    return None


def clean_int(text):
    """
    Convert:
        '#1,234'
    into:
        1234
    """

    if text is None:
        return None

    try:
        return int(str(text).replace("#", "").replace(",", "").strip())

    except Exception:
        return None


def clean_float(text):
    """
    Convert string score to float.
    """

    if text is None:
        return None

    try:
        return float(str(text).strip())

    except Exception:
        return None


# ============================================================
# DOWNLOAD USER LIST
# ============================================================


def get_my_list():
    """
    Download the user's anime list using MAL's
    load.json endpoint.

    Uses local caching to reduce requests.

    Exports the full list to:
        output/my_list.csv
    """

    cache_file = f"{CACHE_DIR}/my_list_{USERNAME}.json"

    if cache_is_valid(cache_file):

        print(f"Using cached {Path(cache_file).name}")

        with open(cache_file, "r", encoding="utf-8") as f:
            anime_data = json.load(f)

    else:

        print("\nDownloading MyAnimeList data...")

        anime_data = []
        offset = 0

        while True:

            url = f"https://myanimelist.net/animelist/{USERNAME}/load.json"

            response = requests.get(
                url,
                params={"status": 7, "offset": offset},
                headers=HEADERS,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            if not data:
                break

            anime_data.extend(data)

            print(f"Fetched records " f"(Total: {len(anime_data)})")

            offset += len(data)

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(anime_data, f, indent=2)

    rows = []

    for anime in anime_data:
        rows.append(
            {
                "anime_id": anime["anime_id"],
                "anime_title": anime["anime_title"],
                "anime_title_eng": anime.get("anime_title_eng"),
                "status": USER_STATUS_MAP.get(anime["status"], anime["status"]),
                "anime_airing_status": AIRING_STATUS_MAP.get(
                    anime["anime_airing_status"], anime["anime_airing_status"]
                ),
                "anime_media_type_string": anime["anime_media_type_string"],
                "anime_mpaa_rating_string": anime["anime_mpaa_rating_string"],
                "anime_num_episodes": anime["anime_num_episodes"],
                "anime_popularity": anime["anime_popularity"],
                "anime_score_val": anime["anime_score_val"],
                "anime_total_members": anime["anime_total_members"],
                "anime_total_scores": anime["anime_total_scores"],
                "anime_url": "https://myanimelist.net" + anime["anime_url"],
                "genres": ", ".join(g["name"] for g in anime.get("genres", [])),
            }
        )

    df = pd.DataFrame(rows)

    df.to_csv(f"{OUTPUT_DIR}/my_list.csv", index=False)

    return df


# ============================================================
# DOWNLOAD TOP ANIME BY POPULARITY
# ============================================================


def get_top_anime():
    """
    Retrieve the most popular anime from MAL's
    Top Anime by Popularity rankings.

    The number of pages scraped is controlled
    by TOP_PAGES.

    Results are cached and exported to:
        cache/top_anime.csv
    """

    cache_file = f"{CACHE_DIR}/top_anime.csv"

    if cache_is_valid(cache_file):
        print("Using cached top_anime.csv")

        return pd.read_csv(cache_file)

    print("\nDownloading Top Anime By Popularity...")

    rows = []

    for page in range(TOP_PAGES):

        limit = page * 50

        url = "https://myanimelist.net/topanime.php" f"?type=bypopularity&limit={limit}"

        print(f"Scraping page {page + 1}/{TOP_PAGES}")

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        anime_rows = soup.select("tr.ranking-list")

        for row in anime_rows:

            title_elem = row.select_one("h3.anime_ranking_h3 a")
            rank_elem = row.select_one(".rank span")
            score_elem = row.select_one(".score-label")

            if not title_elem:
                continue

            anime_url = title_elem["href"].strip()
            anime_id = extract_id(anime_url)

            if anime_id is None:
                continue

            rows.append(
                {
                    "anime_id": anime_id,
                    "rank": clean_int(rank_elem.text) if rank_elem else None,
                    "title": title_elem.text.strip(),
                    "score": clean_float(score_elem.text) if score_elem else None,
                    "anime_url": anime_url,
                }
            )

    df = pd.DataFrame(rows).drop_duplicates(subset="anime_id")

    df.to_csv(cache_file, index=False)

    return df


# ============================================================
# BUILD RECOMMENDATIONS
# ============================================================


def build_recommendations(my_df, top_df):
    """
    Build recommendation candidates.

    Recommendations are generated from the
    popular anime list and filtered by:

    - Not Completed
    - Not Dropped
    - Score >= MIN_SCORE

    Currently Watching, On Hold, and
    Planned To Watch entries remain eligible.

    Results are exported to:
        output/recommendations.csv
    """

    excluded_ids = set(
        my_df.loc[my_df["status"].isin(["Completed", "Dropped"]), "anime_id"]
    )

    recommendations = top_df[~top_df["anime_id"].isin(excluded_ids)].copy()

    recommendations = recommendations[recommendations["score"] >= MIN_SCORE].copy()

    enrichment_columns = ["anime_id", "status"]

    recommendations = recommendations.merge(
        my_df[enrichment_columns], on="anime_id", how="left"
    )

    recommendations = recommendations.sort_values(
        by="score", ascending=False
    ).reset_index(drop=True)

    recommendations.to_csv(f"{OUTPUT_DIR}/recommendations.csv", index=False)

    return recommendations


# ============================================================
# HTML REPORT
# ============================================================


def generate_html_report(df):
    """
    Generate an interactive HTML report.

    Features:
    - Clickable MAL links
    - Rank sorting
    - Score sorting
    - Year sorting
    - English/Japanese title toggle
    - User list status highlighting

    Output:
        output/recommendations.html
    """

    html_df = df.head(HTML_ROWS).copy()

    details_rows = []

    for _, row in html_df.iterrows():
        details = get_anime_details(row["anime_id"], row["anime_url"])
        details_rows.append(details)

    details_df = pd.DataFrame(details_rows)
    details_df = details_df.rename(columns={"english_title": "scraped_english_title"})

    html_df = pd.concat([html_df.reset_index(drop=True), details_df], axis=1)

    html_df["status"] = html_df["status"].fillna("")
    html_df["genres"] = html_df["genres"].fillna("")
    html_df["english_title"] = (
        html_df["scraped_english_title"].replace("", pd.NA).fillna(html_df["title"])
    )

    rows = []

    for _, row in html_df.iterrows():
        row_color = "#e8f5e9" if row["status"] else "white"

        rows.append(f"""
            <tr style="background-color:{row_color}">
                <td>{row['rank']}</td>

                <td> 
                    <a href="{row['anime_url']}" target="_blank"> 
                        <span class="jp-title"> {row['title']} </span> 
                        <span class="en-title" style="display:none;"> {row['english_title']} </span> 
                    </a> 
                </td>

                <td>{row['score']}</td>
                <td>{row['status']}</td>
                <td>{row['type']}</td>
                <td>{row['episodes']}</td>
                <td>{row['year']}</td>
                <td>{row['genres']}</td>
            </tr>
            """)

    html = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>MAL Recommendations</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 20px;
}}

table {{ width: 100%; }}

th, td {{
    border: 1px solid #ddd;
    padding: 8px;
}}

tr:hover {{ background-color: #f5f5f5; }}

a {{ text-decoration: none; }}

th {{
    background-color: #2e51a2;
    color: white;
    user-select: none;
}}

th.sortable {{ cursor: pointer; }}

th.sortable:hover {{ background-color: #1f3d7a; }}

</style>

</head>

<body>

<h1>MyAnimeList Recommendations - {USERNAME}</h1>

<p> Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} </p>

<button id="titleButton" onclick="toggleTitles()"> Show English Titles </button>

<table id="animeTable">

<thead>

<tr>
    <th class="sortable" onclick="sortTable(0, true)">
        Rank ↕
    </th>

    <th>Title</th>

    <th class="sortable" onclick="sortTable(2, true)">
        Score ↕
    </th>
    
    <th>My List Status</th>
    <th>Type</th>
    <th>Episodes</th>
    
    <th class="sortable" onclick="sortTable(6, true)">
        Year ↕
    </th>
    
    <th>Genres</th>
</tr>

</thead>

<tbody>

{''.join(rows)}

</tbody>

</table>

<script>

let currentSortColumn = -1;
let ascending = true;

function sortTable(columnIndex, isNumeric) {{

    const table = document.getElementById("animeTable");
    const tbody = table.querySelector("tbody");
    const rows = Array.from( tbody.querySelectorAll("tr") );

    if (currentSortColumn === columnIndex) {{
        ascending = !ascending;
    }} else {{
        ascending = true;
        currentSortColumn = columnIndex;
    }}

    rows.sort((a, b) => {{

        let aVal = a.cells[columnIndex] .innerText .trim();

        let bVal = b.cells[columnIndex] .innerText .trim();

        if (isNumeric) {{
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        }} else {{
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }}

        if (ascending) {{ return aVal > bVal ? 1 : -1; }}

        return aVal < bVal ? 1 : -1;
        
    }});

    rows.forEach(row => tbody.appendChild(row) );

}}

let showEnglish = false;

function toggleTitles() {{

    showEnglish = !showEnglish;
    
    document
        .getElementById("titleButton")
        .innerText =
            showEnglish
            ? "Show Japanese Titles"
            : "Show English Titles";

    document
        .querySelectorAll(".jp-title")
        .forEach(el => {{
            el.style.display =
                showEnglish
                ? "none"
                : "inline";
        }});

    document
        .querySelectorAll(".en-title")
        .forEach(el => {{
            el.style.display =
                showEnglish
                ? "inline"
                : "none";
        }});
}}

</script>

</body>

</html>
"""

    html_file = f"{OUTPUT_DIR}/recommendations.html"

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)

    html_path = Path(html_file).resolve()

    webbrowser.open(f"file://{html_path}")


# ============================================================
# MAIN
# ============================================================


def main():
    """
    Application entry point.
    """

    print("\n=== MAL Recommendation Analyzer ===")

    CONFIG = load_config()

    global USERNAME
    global TOP_PAGES
    global CACHE_HOURS
    global MIN_SCORE
    global HTML_ROWS

    USERNAME = CONFIG["username"]
    TOP_PAGES = CONFIG["top_pages"]
    CACHE_HOURS = CONFIG["cache_hours"]
    MIN_SCORE = CONFIG["min_score"]
    HTML_ROWS = CONFIG["html_rows"]

    if not USERNAME:
        USERNAME = input("\nEnter your MyAnimeList username: ").strip()

        CONFIG["username"] = USERNAME

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=2)

    my_df = get_my_list()

    top_df = get_top_anime()

    recommendations = build_recommendations(
        my_df,
        top_df,
    )

    print("\n")

    generate_html_report(recommendations)


if __name__ == "__main__":
    main()
