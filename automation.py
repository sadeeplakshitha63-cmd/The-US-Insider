import google.generativeai as genai
import feedparser
import os
import re
import requests
from datetime import datetime
import time

# API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def get_us_trends():
    """Fetch US trending topics using multiple fallback sources."""
    print("Fetching US trends...")
    
    # Method 1: Try Google Trends RSS with a custom User-Agent
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(
            "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            if feed.entries:
                trends = [entry.title for entry in feed.entries[:3]]
                print(f"Found trends from Google: {trends}")
                return trends
    except Exception as e:
        print(f"Google Trends failed: {e}")

    # Method 2: Fallback - Reddit r/news top posts
    try:
        headers = {'User-Agent': 'TheUSInsiderBot/1.0'}
        response = requests.get(
            "https://www.reddit.com/r/news/top.json?limit=5&t=day",
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            posts = data['data']['children']
            trends = [post['data']['title'][:80] for post in posts[:3]]
            print(f"Found trends from Reddit: {trends}")
            return trends
    except Exception as e:
        print(f"Reddit fallback failed: {e}")

    # Method 3: Hard-coded backup topics (always works)
    print("Using backup trending topics...")
    backup_topics = [
        "AI Revolution: How Artificial Intelligence is Reshaping American Jobs in 2025",
        "The Future of Healthcare: New Breakthroughs Transforming Patient Care in the USA",
        "Personal Finance Tips: How Americans Are Saving More Money in 2025"
    ]
    return backup_topics

def ask_gemini(topic):
    """Generate an article using Gemini AI."""
    print(f"Generating article for: {topic}")
    
    # Use gemini-1.5-flash (faster, free tier compatible)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""You are an expert American journalist writing for 'The US Insider' — a premium news blog for US readers.

Write a comprehensive, engaging blog post about: "{topic}"

Requirements:
- Write ONLY in Markdown format
- Do NOT include a title (H1) at the start — I will add that separately
- Use H2 and H3 subheadings to structure the content
- Use bullet points where appropriate
- Tone: Authoritative, knowledgeable, written like a real American expert (NOT like AI)
- Length: 650-900 words
- Include real facts, statistics, and actionable insights
- End with a strong conclusion paragraph

Start writing the article content directly:"""

        response = model.generate_content(prompt)
        print("Article generated successfully!")
        return response.text
    except Exception as e:
        print(f"gemini-1.5-flash failed: {e}")
    
    # Fallback to gemini-pro
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"Write a 700 word blog post about: {topic}. Use markdown headings and bullet points.")
        return response.text
    except Exception as e:
        print(f"gemini-pro also failed: {e}")
        return None

def save_article(title, content):
    """Save article as Jekyll markdown post."""
    print(f"Saving article: {title}")
    
    if not os.path.exists('_posts'):
        os.makedirs('_posts')
        
    date_str = datetime.now().strftime('%Y-%m-%d')
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    filename = f"{date_str}-{clean_title.strip().replace(' ', '-').lower()[:60]}.md"
    filepath = os.path.join('_posts', filename)
    
    if os.path.exists(filepath):
        print(f"Article already exists: {filepath}. Skipping.")
        return False
        
    # Add timezone offset to avoid Jekyll warnings
    now = datetime.now()
    date_formatted = now.strftime('%Y-%m-%d %H:%M:%S +0000')
        
    front_matter = f"""---
layout: post
title: "{title.replace('"', "'")}"
date: {date_formatted}
categories: [Trends, USA]
description: "Read the latest insights on {title[:100]} from The US Insider."
---

"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter + content)
    print(f"✅ Successfully saved: {filepath}")
    return True

if __name__ == "__main__":
    print("🚀 The US Insider - Auto Content Engine Starting...")
    
    trends = get_us_trends()
    if not trends:
        print("❌ No trends found. Exiting.")
        exit(1)
        
    print(f"📊 Top trend today: {trends[0]}")
    
    article_content = ask_gemini(trends[0])
    if article_content:
        saved = save_article(trends[0], article_content)
        if saved:
            print("🎉 Article published successfully!")
        else:
            print("ℹ️ Article already published today.")
    else:
        print("❌ Failed to generate article content.")
        exit(1)
