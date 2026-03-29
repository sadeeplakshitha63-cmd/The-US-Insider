import os
import re
import requests
from datetime import datetime

# API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

# ─── Unsplash keyword mapping for real photos ──────────────────────────────────
def get_photo_keywords(topic):
    """Extract relevant keywords from topic for Unsplash image search."""
    topic_lower = topic.lower()
    
    keyword_map = {
        'health':     'healthcare,hospital,doctors,medicine',
        'disease':    'hospital,healthcare,medical,science',
        'ai':         'technology,artificial-intelligence,computer,data',
        'tech':       'technology,innovation,digital,silicon-valley',
        'finance':    'finance,stock-market,money,business,wall-street',
        'economy':    'economy,business,stock-market,trading',
        'food':       'food,restaurant,cooking,american-food',
        'climate':    'nature,climate,environment,earth',
        'election':   'politics,flag,usa,washington',
        'jobs':       'business,office,work,career',
        'crypto':     'cryptocurrency,bitcoin,blockchain,digital',
        'housing':    'real-estate,home,housing,suburb',
        'education':  'education,university,learning,campus',
        'military':   'military,army,usa,defense',
        'sport':      'sports,american-football,stadium',
    }
    
    for key, keywords in keyword_map.items():
        if key in topic_lower:
            return keywords
    
    # Default: general American / news image
    return 'usa,american,news,city'

def get_unsplash_image(topic):
    """Get a relevant image URL from Unsplash Source (no API key needed)."""
    keywords = get_photo_keywords(topic)
    # Unsplash Source URL — free, no auth, returns real high-quality photos
    url = f"https://source.unsplash.com/1200x630/?{keywords}"
    
    try:
        # Follow redirects to get the actual image URL
        response = requests.head(url, allow_redirects=True, timeout=10)
        if response.status_code == 200:
            final_url = response.url
            print(f"✅ Found photo: {final_url[:80]}...")
            return final_url
        else:
            print(f"Unsplash returned {response.status_code}")
    except Exception as e:
        print(f"Image fetch failed: {e}")
    
    # Fallback: use a curated American-themed Unsplash photo if lookup fails
    fallback_ids = {
        'tech':    'photo-1518770660439-4636190af475',
        'health':  'photo-1576091160550-2173ff9e5ee5',
        'finance': 'photo-1611974789855-9c2a0a7236a3',
        'default': 'photo-1501594907352-04cda38ebc29',  # USA landscape
    }
    topic_lower = topic.lower()
    if 'tech' in topic_lower or 'ai' in topic_lower:
        fid = fallback_ids['tech']
    elif 'health' in topic_lower or 'disease' in topic_lower:
        fid = fallback_ids['health']
    elif 'finance' in topic_lower or 'economy' in topic_lower:
        fid = fallback_ids['finance']
    else:
        fid = fallback_ids['default']
    
    return f"https://images.unsplash.com/{fid}?w=1200&h=630&fit=crop"

# ─── Trend Fetching ────────────────────────────────────────────────────────────
def get_us_trends():
    """Fetch US trending topics using multiple fallback sources."""
    print("Fetching US trends...")
    
    try:
        headers = {'User-Agent': 'TheUSInsiderBot/2.0'}
        response = requests.get(
            "https://www.reddit.com/r/news/top.json?limit=5&t=day",
            headers=headers, timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            posts = data['data']['children']
            trends = [post['data']['title'][:80] for post in posts[:3]]
            print(f"Found trends from Reddit: {trends}")
            return trends
    except Exception as e:
        print(f"Reddit failed: {e}")

    print("Using backup trending topics...")
    return [
        "AI Revolution: How Artificial Intelligence is Reshaping American Jobs in 2026",
        "The Future of Healthcare: New Breakthroughs Transforming Patient Care in the USA",
        "Personal Finance Tips: How Americans Are Saving More Money in 2026"
    ]

# ─── Gemini Article Generation ─────────────────────────────────────────────────
def ask_gemini(topic):
    """Generate an article using Gemini REST API directly."""
    print(f"Generating article for: {topic}")
    
    prompt = f"""You are an expert American journalist writing for 'The US Insider' — a premium news magazine.

Write a comprehensive, engaging article about: "{topic}"

Requirements:
- Write ONLY in Markdown format
- Do NOT include a title (H1) at the start
- Use H2 and H3 subheadings
- Use bullet points where appropriate
- Tone: Authoritative, like a real American expert — NOT like AI
- Length: 700-900 words
- Include real-sounding facts, data points, and actionable insights
- End with a strong conclusion paragraph"""

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash-8b",
        "gemini-pro"
    ]
    
    headers = {'Content-Type': 'application/json'}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7}
    }
    
    for model in models_to_try:
        print(f"  → Trying model: {model}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            r = requests.post(url, headers=headers, json=body, timeout=30)
            if r.status_code == 200:
                text = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if text:
                    print(f"✅ Article generated using {model}!")
                    return text
            else:
                print(f"  ✗ {model} → HTTP {r.status_code}")
        except Exception as e:
            print(f"  ✗ {model} → crashed: {e}")
    
    print("❌ All models failed.")
    return None

# ─── Save Article ──────────────────────────────────────────────────────────────
def save_article(title, content, image_url):
    """Save article as Jekyll post with image in front matter."""
    print(f"Saving: {title}")
    
    if not os.path.exists('_posts'):
        os.makedirs('_posts')
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    filename = f"{date_str}-{clean_title.strip().replace(' ', '-').lower()[:60]}.md"
    filepath = os.path.join('_posts', filename)
    
    if os.path.exists(filepath):
        print(f"Already exists: {filepath}. Skipping.")
        return False
    
    date_formatted = datetime.now().strftime('%Y-%m-%d %H:%M:%S +0000')
    excerpt = ' '.join(content.split()[:30]) + '...'
    
    front_matter = f"""---
layout: post
title: "{title.replace('"', "'")}"
date: {date_formatted}
categories: [Trends, USA]
image: "{image_url}"
excerpt: "{excerpt.replace('"', "'")}"
---

"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter + content)
    print(f"✅ Saved: {filepath}")
    return True

# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 The US Insider – Auto Content Engine Starting...")
    
    trends = get_us_trends()
    if not trends:
        print("❌ No trends found.")
        exit(1)
    
    topic = trends[0]
    print(f"📊 Today's topic: {topic}")
    
    # Fetch real photo and generate article in parallel logic
    image_url = get_unsplash_image(topic)
    article_content = ask_gemini(topic)
    
    if article_content:
        saved = save_article(topic, article_content, image_url)
        if saved:
            print("🎉 Article published!")
        else:
            print("ℹ️ Already published today.")
    else:
        print("❌ Failed to generate article.")
        exit(1)
