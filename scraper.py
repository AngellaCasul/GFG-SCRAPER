import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ── ALL AVAILABLE TOPICS ─────────────────────────────────────
TOPICS = {
    "Python":                       "https://www.geeksforgeeks.org/python-programming-language/",
    "Java":                         "https://www.geeksforgeeks.org/java/",
    "JavaScript":                   "https://www.geeksforgeeks.org/javascript/",
    "C":                            "https://www.geeksforgeeks.org/c-programming-language/",
    "C++":                          "https://www.geeksforgeeks.org/c-plus-plus/",
    "PHP":                          "https://www.geeksforgeeks.org/php-tutorial/",
    "R":                            "https://www.geeksforgeeks.org/r-programming-language/",
    "Linux":                        "https://www.geeksforgeeks.org/linux-tutorial/",
    "Machine Learning":             "https://www.geeksforgeeks.org/machine-learning/",
    "Artificial Intelligence":      "https://www.geeksforgeeks.org/artificial-intelligence/",
    "Data Analysis":                "https://www.geeksforgeeks.org/data-analysis-tutorial/",
    "Data Science":                 "https://www.geeksforgeeks.org/data-science-tutorial/",
    "Software Engineering":         "https://www.geeksforgeeks.org/software-engineering/",
    "Web Technology":               "https://www.geeksforgeeks.org/web-technology/",
    "Software Testing":             "https://www.geeksforgeeks.org/software-testing-tutorial/",
    "Data Warehousing":             "https://www.geeksforgeeks.org/data-warehousing/",
    "Cybersecurity":                "https://www.geeksforgeeks.org/cyber-security-tutorial/",
    "Operating Systems":            "https://www.geeksforgeeks.org/operating-systems/",
    "Distributed Systems":          "https://www.geeksforgeeks.org/distributed-systems-tutorial/",
    "Computer Organization":        "https://www.geeksforgeeks.org/computer-organization-and-architecture-tutorials/",
    "DevOps":                       "https://www.geeksforgeeks.org/devops-tutorial/",
    "Computer Networks":            "https://www.geeksforgeeks.org/computer-network-tutorials/",
    "DBMS":                         "https://www.geeksforgeeks.org/dbms/",
    "Web Development":              "https://www.geeksforgeeks.org/web-development/",
    "HTML":                         "https://www.geeksforgeeks.org/html-tutorial/",
    "CSS":                          "https://www.geeksforgeeks.org/css-tutorial/",
    "Ruby":                         "https://www.geeksforgeeks.org/ruby-programming-language/",
    "Go":                           "https://www.geeksforgeeks.org/golang/",
}


# ── STEP 1: DISCOVER ARTICLE URLS FROM TOPIC PAGE ────────────
def get_article_urls(topic_name, max_articles=12):
    """Visits the topic page and extracts article links dynamically."""
    base_url = TOPICS.get(topic_name)
    if not base_url:
        return []

    try:
        response = requests.get(base_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching topic page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]

        # Must be a GFG article link
        if not href.startswith("https://www.geeksforgeeks.org/"):
            continue

        # Skip the topic page itself
        if href == base_url:
            continue

        # Skip non-article pages
        skip_keywords = [
            "category", "tag", "page", "login", "register",
            "write", "contribute", "jobs", "courses", "practice",
            "contest", "interview", "quiz", "#", "?",
            "projects", "cheat-sheet", "exercise", "mcq",
            "interview-questions", "multiple-choice"
        ]
        if any(kw in href.lower() for kw in skip_keywords):
            continue

        # Must look like an article (has slug with dashes)
        slug = href.replace("https://www.geeksforgeeks.org/", "").strip("/")
        if "-" not in slug or len(slug) < 5:
            continue

        if href not in seen:
            seen.add(href)
            urls.append(href)

        if len(urls) >= max_articles:
            break

    return urls


# ── STEP 2: SCRAPE ONE ARTICLE ───────────────────────────────
def scrape_article(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return {
            "url": url,
            "title": "Not Available",
            "concepts": "Not Available",
            "difficulty": "Not Available",
            "code_snippets": ["Not Available"],
            "complexity": ["Not Available"],
            "related_links": [{"title": "Not Available", "url": ""}],
            "scraped_at": datetime.now().isoformat(),
        }

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. TITLE
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Not Available"

    # 2. CONCEPTS
    concepts = "Not Available"
    containers = [
        soup.find("div", class_=re.compile(r"article--container", re.I)),
        soup.find("div", class_=re.compile(r"entry-content", re.I)),
        soup.find("article"),
        soup.find("main"),
    ]
    for container in containers:
        if container:
            for p in container.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 100 and "cookie" not in text.lower() and "advertisement" not in text.lower():
                    concepts = text
                    break
        if concepts != "Not Available":
            break

    if concepts == "Not Available":
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 100 and "cookie" not in text.lower():
                concepts = text
                break

    # 3. DIFFICULTY
    difficulty = "Not Available"
    for tag in soup.find_all(True):
        text = tag.get_text(strip=True).lower()
        if text in ["easy", "medium", "hard", "basic", "expert"] and len(text) < 15:
            difficulty = text.capitalize()
            break

    if difficulty == "Not Available":
        combined = title.lower() + " " + concepts.lower()
        if any(w in combined for w in ["introduction", "basics", "what is", "overview", "getting started", "beginner"]):
            difficulty = "Easy"
        elif any(w in combined for w in ["advanced", "optimization", "machine learning", "algorithm", "complex", "expert"]):
            difficulty = "Hard"
        else:
            difficulty = "Medium"

    # 4. CODE SNIPPETS
    code_snippets = []
    for block in soup.find_all("pre")[:3]:
        code_text = block.get_text(strip=True)
        if len(code_text) > 10:
            code_snippets.append(code_text)
    if not code_snippets:
        code_snippets = ["Not Available"]

    # 5. COMPLEXITY
    complexity = []
    for tag in soup.find_all(["p", "li", "td", "span", "div"]):
        text = tag.get_text(strip=True)
        if re.search(r'(time|space)\s*complexity', text, re.IGNORECASE):
            if 5 < len(text) < 400 and text not in complexity:
                complexity.append(text)

    if not complexity:
        for line in soup.get_text().splitlines():
            line = line.strip()
            if re.search(r'(time|space)\s*complexity', line, re.IGNORECASE):
                if 5 < len(line) < 300 and line not in complexity:
                    complexity.append(line)

    if not complexity:
        complexity = ["Not Available"]

    # 6. RELATED LINKS
    related_links = []
    seen = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        link_text = a_tag.get_text(strip=True)
        if (
            href.startswith("https://www.geeksforgeeks.org/")
            and href != url
            and len(link_text) > 5
            and "#" not in href
            and href not in seen
        ):
            seen.add(href)
            related_links.append({"title": link_text, "url": href})
    related_links = related_links[:5]
    if not related_links:
        related_links = [{"title": "Not Available", "url": ""}]

    return {
        "url": url,
        "title": title,
        "concepts": concepts,
        "difficulty": difficulty,
        "code_snippets": code_snippets,
        "complexity": complexity,
        "related_links": related_links,
        "scraped_at": datetime.now().isoformat(),
    }


# ── STEP 3: SCRAPE ALL SELECTED TOPICS ───────────────────────
def run_scraper(selected_topics, progress_callback=None):
    """Scrapes articles for each selected topic and saves to JSON."""
    os.makedirs("data", exist_ok=True)
    all_results = {}

    for topic in selected_topics:
        if progress_callback:
            progress_callback(f"Finding articles for: {topic}")

        urls = get_article_urls(topic)

        if not urls:
            if progress_callback:
                progress_callback(f"No articles found for {topic}, skipping...")
            continue

        if progress_callback:
            progress_callback(f"Found {len(urls)} articles for {topic}")

        articles = []
        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(f"  Scraping {i+1}/{len(urls)}: {url.split('/')[-2].replace('-', ' ').title()}")

            article = scrape_article(url)

            # Skip articles that have no useful content
            if article["concepts"] == "Not Available" and article["code_snippets"] == ["Not Available"]:
                if progress_callback:
                    progress_callback(f"  Skipping (no content): {url.split('/')[-2]}")
                continue

            articles.append(article)

            if i < len(urls) - 1:
                time.sleep(2)

        all_results[topic] = articles

    # Save to JSON
    save_path = "data/scraped_topics.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "selected_topics": selected_topics,
            "results": all_results
        }, f, indent=2)

    if progress_callback:
        progress_callback("Done! All topics scraped successfully.")

    return all_results


# ── HELPERS ──────────────────────────────────────────────────
def load_data():
    path = "data/scraped_topics.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def has_data():
    return os.path.exists("data/scraped_topics.json")


def get_topics():
    return list(TOPICS.keys())