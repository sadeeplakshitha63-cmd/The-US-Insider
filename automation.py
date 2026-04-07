import os
import re
import requests
import feedparser
import json
import random
import time
from datetime import datetime, timedelta
from duckduckgo_search import DDGS

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

# RSS Feeds for Different Categories - Expanded for more variety and niche traffic
FEEDS = {
    "US News": [
        "http://rss.cnn.com/rss/cnn_topstories.rss", 
        "http://feeds.foxnews.com/foxnews/national",
        "https://www.huffpost.com/section/front-page/feed"
    ],
    "Health & Disease": [
        "https://khn.org/feed/", 
        "https://www.statnews.com/feed/",
        "https://www.medicalnewstoday.com/feed"
    ],
    "Tech & AI": [
        "https://techcrunch.com/feed/", 
        "https://www.wired.com/feed/rss",
        "https://venturebeat.com/feed/",
        "https://www.theverge.com/rss/index.xml"
    ],
    "Finance & Crypto": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000",
        "https://feeds.a.dj.com/rss/WSJLinks.xml",
        "https://cointelegraph.com/rss/tag/bitcoin"
    ],
    "Lifestyle & Travel": [
        "https://www.lonelyplanet.com/news/rss",
        "https://www.lifehack.org/feed"
    ]
}

def get_image(query):
    """Fetch a real image from Google/DDG based on the query."""
    print(f"Searching for image: {query}")
    try:
        results = DDGS().images(query, max_results=1)
        if results and len(results) > 0:
            return results[0]['image']
    except Exception as e:
        print(f"Image search failed: {e}")
    # Fallback to high-quality curated stock images
    fallbacks = [
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200",
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200"
    ]
    return random.choice(fallbacks)

def ask_gemini(prompt):
    models_to_try = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.8}}
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if text:
                    return text
        except Exception:
            pass
    return None

def fetch_and_rewrite():
    # We will pick 4 random categories to generate articles
    categories_to_process = list(FEEDS.keys())
    random.shuffle(categories_to_process)
    
    articles_generated = 0
    
    for category in categories_to_process[:4]:
        feed_url = random.choice(FEEDS[category])
        print(f"Fetching from {feed_url}...")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
                
            entry = random.choice(feed.entries[:8])
            base_title = entry.title
            
            # Slug generation
            safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', base_title).strip().replace(' ', '-').lower()[:50]
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Deduplication
            if any(safe_title in f for f in os.listdir('_posts') if f.endswith('.md')):
                print(f"Skipping already covered topic: {base_title}")
                continue
                
            print(f"\n--- Generating Viral Article for {category}: {base_title} ---")
            
            # Prompt Gemini for high SEO value and Viral potential
            prompt = f"""You are a top-tier investigative journalist at 'The US Insider'. 
Your task is to write a VIRAL, high-authority news story based on: "{base_title}"

DIRECTIONS FOR VIRAL CONTENT:
1. THE TONE: Opinionated, authoritative, and deeply analytical. Use a mix of long, thoughtful periods and short, impactful sentences.
2. BEYOND THE NEWS: Explain WHY this happened, WHO it benefits, and WHAT the reader should do now.
3. STRUCTURE:
   - Catchy, click-worthy Headline.
   - Intriguing introduction (hook).
   - Use H2 and H3 subheadings with keywords.
   - Include a 'Quick Take' section with bullet points.
   - Add a 'Future Outlook' section.
4. SEO:
   - Naturally integrate keywords related to {category} and "{base_title}".
   - Target 800 - 1200 words.
5. NO AI CLICHES: Do not use "In today's world", "Only time will tell", or "It's important to remember".

Output format must be EXCLUSIVELY VALID JSON:
{{
  "headline": "A viral, high-CTR headline.",
  "article": "Your markdown formatted body content (no H1).",
  "description": "A compelling 155-character meta description.",
  "image_alt": "Keyword-rich alt text.",
  "social_caption": "A viral Twitter/X thread starter or Pinterest description (200 chars).",
  "keywords": "comma, separated, keywords",
  "comments": [
    {{"name": "Diverse American Name", "time": "Relative Time", "text": "Thoughtful insight."}}
  ]
}}
Generate 6 unique reader comments. No other text."""

            response_text = ask_gemini(prompt)
            if not response_text:
                continue
                
            # Clean JSON
            json_str = response_text.strip()
            if '```' in json_str:
                json_str = json_str.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
                
            try:
                data = json.loads(json_str.strip())
                final_title = data.get('headline', base_title)
                article_body = data.get('article', '')
                comments = data.get('comments', [])
                meta_desc = data.get('description', '')
                image_alt = data.get('image_alt', '')
                keywords = data.get('keywords', '')
                social_caption = data.get('social_caption', '')
                
                if len(article_body) < 100:
                    continue
                    
                image_url = get_image(base_title)
                date_formatted = datetime.now().strftime('%Y-%m-%d %H:%M:%S +0000')
                filename = f"{date_str}-{safe_title}.md"
                filepath = os.path.join('_posts', filename)
                
                # Format comments
                comments_yaml = "comments:\n"
                for c in comments:
                    safe_text = str(c.get('text', '')).replace('"', "'")
                    comments_yaml += f"  - name: \"{c.get('name', 'Anonymous')}\"\n"
                    comments_yaml += f"    time: \"{c.get('time', 'Just now')}\"\n"
                    comments_yaml += f"    text: \"{safe_text}\"\n"
                
                # Full Frontmatter
                front_matter = f"""---
layout: post
title: "{final_title.replace('"', "'")}"
date: {date_formatted}
categories: [{category.replace(' & ', ', ')}]
image: "{image_url}"
image_alt: "{image_alt.replace('"', "'")}"
description: "{meta_desc.replace('"', "'")}"
keywords: "{keywords}"
social_promo: "{social_caption.replace('"', "'")}"
{comments_yaml}---

"""
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(front_matter + article_body)
                    
                print(f"✅ Created: {filename}")
                articles_generated += 1
                time.sleep(15) 
                
            except Exception as e:
                print(f"JSON Error: {e}")
                
        except Exception as e:
            print(f"Error: {e}")
            
    print(f"\n🚀 Success: Generated {articles_generated} stories.")

if __name__ == "__main__":
    if not os.path.exists('_posts'):
        os.makedirs('_posts')
    fetch_and_rewrite()
