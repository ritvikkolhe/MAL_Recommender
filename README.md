# MyAnimeList Recommendation Analyzer

A Python tool that analyzes a public MyAnimeList (MAL) profile and generates personalized anime recommendations from MAL's most popular anime.

The analyzer automatically filters out anime you've already completed or dropped, enriches recommendations with metadata from MyAnimeList, and generates an interactive HTML report with sorting and title-toggle functionality.

---

## Features

✅ Downloads and analyzes a public MyAnimeList anime list

✅ Uses configurable caching to minimize requests and improve performance

✅ Builds recommendations from the Top N most popular anime (default: Top 250)

✅ Excludes:
- Completed anime
- Dropped anime

✅ Keeps visible:
- Currently Watching
- On Hold
- Planned To Watch

✅ Filters recommendations using a configurable minimum score

✅ Scrapes and caches additional metadata:
- English title
- Anime type
- Episode count
- Release year
- Genres

✅ Exports recommendations to CSV

✅ Generates an interactive HTML report with:
- Clickable MyAnimeList links
- Sortable Rank column
- Sortable Score column
- Sortable Year column
- Japanese / English title toggle
- Highlighting for anime already on your list

✅ Automatically opens the generated report

---

## Example Workflow

```text
MyAnimeList Profile
        │
        ▼
Download Anime List
        │
        ▼
Get Top Popular Anime
        │
        ▼
Remove Completed + Dropped
        │
        ▼
Apply Score Filter
        │
        ▼
Scrape Metadata
        │
        ▼
Generate CSV + HTML Report
```

---

## Requirements

- Python 3.10+
- Internet connection
- Public MyAnimeList profile

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/mal-recommendation-analyzer.git

cd mal-recommendation-analyzer
```

Install dependencies:

```bash
pip install pandas requests beautifulsoup4 lxml
```

---

## Configuration

On first launch, the script automatically creates:

```text
cache/config.json
```

Example:

```json
{
  "username": "your_mal_username",
  "top_pages": 5,
  "cache_hours": 24,
  "min_score": 8.0,
  "html_rows": 30
}
```

### Configuration Options

| Setting | Description |
|----------|------------|
| username | MyAnimeList username |
| top_pages | Number of Top Anime pages to scrape (50 anime per page) |
| cache_hours | Cache lifetime before refreshing |
| min_score | Minimum MAL rating required |
| html_rows | Number of recommendations displayed in HTML report |

---

## Usage

Run:

```bash
python mal_recommender.py
```

If no username is configured, the script will prompt for one:

```text
Enter your MyAnimeList username:
```

The username is then saved automatically.

---

## Output Files

### User Anime List

```text
output/my_list.csv
```

Contains your complete downloaded anime list.

---

### Recommendations CSV

```text
output/recommendations.csv
```

Contains recommendation candidates after filtering.

---

### Interactive HTML Report

```text
output/recommendations.html
```

Features:

- Clickable MAL links
- Sort by Rank
- Sort by Score
- Sort by Year
- Toggle Japanese / English titles
- Highlight anime already on your list

The report automatically opens in your default browser.

---

## Cache Structure

```text
cache/
│
├── config.json
├── my_list_<username>.json
├── top_anime.csv
│
└── anime_details/
    ├── 1.json
    ├── 20.json
    ├── 5114.json
    └── ...
```

### Why Caching?

Caching significantly improves performance by preventing unnecessary requests to MyAnimeList.

Cached data includes:

- User anime lists
- Popular anime rankings
- Anime metadata pages

---

## Recommendation Logic

Recommendations are generated using:

```text
Top Popular Anime
      -
Completed Anime
      -
Dropped Anime
      =
Recommendations
```

Then:

```text
Score >= min_score
```

is applied.

Current status values such as:

- Watching
- On Hold
- Planned To Watch

remain eligible and are highlighted in the report.

---

## Technologies Used

- Python
- Pandas
- Requests
- BeautifulSoup4
- LXML
- HTML
- JavaScript

---

## Performance

The analyzer is optimized for repeated use:

- Cached API responses
- Cached anime metadata
- Cached popularity rankings
- O(1) recommendation exclusion lookups using Python sets
- Metadata fetched only for displayed recommendations

Typical subsequent runs complete in just a few seconds due to cache reuse.

---

## Limitations

- Requires a public MyAnimeList profile
- HTML structure changes on MyAnimeList may require scraper updates
- Recommendations are popularity-based and do not currently use genre or preference matching

---

## Future Ideas

Potential enhancements:

- Genre-based recommendations
- Studio-based recommendations
- Favorite-anime weighting
- Similarity scoring
- Recommendation explanations
- Sequel/prequel detection
- Dark mode HTML report
- Recommendation history tracking

---

## Author

**Ritvik Kolhe**

---

## License

This project is licensed under the MIT License.

Feel free to use, modify, and improve it.
