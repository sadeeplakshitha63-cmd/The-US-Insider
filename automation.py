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

# RSS Feeds for Different Categories
FEEDS = {
    "US News": ["http://rss.cnn.com/rss/cnn_topstories.rss", "http://feeds.foxnews.com/foxnews/national"],
    "Health & Disease": ["https://khn.org/feed/", "https://www.statnews.com/feed/"],
    "Tech": ["https://techcrunch.com/feed/", "https://www.wired.com/feed/rss"],
    "Finance": ["https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000"]
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
    # Fallback highly professional image
    return "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200&h=800&fit=crop"

def ask_gemini(prompt):
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.85}}
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=data, timeout=40)
            if response.status_code == 200:
                result = response.json()
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if text:
                    return text
        except Exception:
            pass
    return None

def fetch_and_rewrite():
    # We will pick 3 random categories and 1 article from each to generate 3 articles per run limit.
    categories_to_process = list(FEEDS.keys())
    random.shuffle(categories_to_process)
    
    articles_generated = 0
    generated_titles = []
    
    for category in categories_to_process[:3]:
        feed_url = random.choice(FEEDS[category])
        print(f"Fetching from {feed_url}...")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
                
            entry = random.choice(feed.entries[:5])
            base_title = entry.title
            
            # Check if we already generated it roughly today
            safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', base_title).strip().replace(' ', '-').lower()[:40]
            date_str = datetime.now().strftime('%Y-%m-%d')
            search_pattern = f"{date_str}-.*{safe_title}.*.md"
            
            # Simple deduplication trick
            if any(safe_title in f for f in os.listdir('_posts') if f.endswith('.md')):
                print(f"Skipping already covered topic: {base_title}")
                continue
                
            print(f"\n--- Generating Article for {category}: {base_title} ---")
            
            # Prompt Gemini to deeply humanize and generate fake comments
            prompt = f"""You are a veteran, award-winning human investigative journalist for 'The US Insider'. 
You have been tasked to completely rewrite and expand upon the following news topic: "{base_title}"

CRITICAL INSTRUCTIONS TO BYPASS AI DETECTORS:
- You must write exactly like a human expert. Use varied sentence lengths (some very short, some long and flowing).
- Include natural transitions, slight conversational idioms, and a confident, authoritative tone.
- Add deep insights, historical context, or statistics that make the article 10x better than standard news.
- Use H2 and H3 subheadings. Use bullet points if necessary.
- Write between 600 - 900 words.
- DO NOT use generic AI intro phrases like "In today's fast-paced world" or "It is important to note".
- Output exactly in JSON format, containing two keys: "article" and "comments".

JSON Format required:
{{
  "article": "Your massive markdown formatted article here. Do not include the H1 title.",
  "comments": [
    {{"name": "John D.", "time": "2 hours ago", "text": "Very insightful perspective, never thought of it this way."}},
    {{"name": "Sarah Jenkins", "time": "35 mins ago", "text": "I disagree with some points, but overall a great read."}}
  ]
}}
Generate exactly 6 realistic, conversational comments from American readers. 
ONLY OUTPUT VALID JSON. No extra text before or after."""

            response_text = ask_gemini(prompt)
            if not response_text:
                print("Gemini failed to respond.")
                continue
                
            # Clean JSON block
            json_str = response_text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
                
            try:
                data = json.loads(json_str.strip())
                article_body = data.get('article', '')
                comments = data.get('comments', [])
                
                if len(article_body) < 100:
                    continue
                    
                # Get a high quality image
                image_url = get_image(base_title)
                
                # Format Date
                date_formatted = datetime.now().strftime('%Y-%m-%d %H:%M:%S +0000')
                filename = f"{date_str}-{safe_title}.md"
                filepath = os.path.join('_posts', filename)
                
                # Process comments into YAML
                comments_yaml = "comments:\n"
                for c in comments:
                    safe_text = str(c.get('text', '')).replace('"', "'")
                    comments_yaml += f"  - name: \"{c.get('name', 'Anonymous')}\"\n"
                    comments_yaml += f"    time: \"{c.get('time', 'Just now')}\"\n"
                    comments_yaml += f"    text: \"{safe_text}\"\n"
                
                # Full Frontmatter
                front_matter = f"""---
layout: post
title: "{base_title.replace('"', "'")}"
date: {date_formatted}
categories: [{category}]
image: "{image_url}"
description: "Exclusive deep dive into {base_title[:50]}..."
{comments_yaml}---

"""
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(front_matter + article_body)
                    
                print(f"✅ Success: {filename}")
                articles_generated += 1
                
                # Sleep briefly to avoid AI rate limits between posts
                time.sleep(10)
                
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                
        except Exception as e:
            print(f"Error fetching from {feed_url}: {e}")
            
    if articles_generated == 0:
        print("❌ Could not generate any articles this run. Might need to try again later.")
    else:
        print(f"🎉 Run complete! Generated {articles_generated} highly humanized articles with photos.")

if __name__ == "__main__":
    print("🚀 The US Insider - Hyper-Human Publishing Engine Starting...")
    if not os.path.exists('_posts'):
        os.makedirs('_posts')
    fetch_and_rewrite()
