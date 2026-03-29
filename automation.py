import google.generativeai as genai
import feedparser
import os
import re
from datetime import datetime
import time

# API Key - Make sure to set this as a GitHub Secret
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def get_us_trends():
    """Fetch the top daily trends from Google Trends for the USA."""
    print("Fetching US Google Trends...")
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    feed = feedparser.parse(url)
    
    trends = []
    for entry in feed.entries[:3]: # Get top 3 trends
        trends.append(entry.title)
    return trends

def ask_gemini(topic):
    """Generate an article using Gemini AI."""
    print(f"Generating article for topic: {topic}")
    
    model = genai.GenerativeModel('gemini-1.5-pro-latest') # Using the latest Gemini model
    
    prompt = f"""
    You are an expert, professional human blogger based in the USA writing for 'The US Insider'.
    Write a comprehensive, engaging, and SEO-optimized blog post about '{topic}'.
    Target audience: USA readers interested in Tech, Health, and Finance/AI.
    Requirements:
    - Write it entirely in Markdown format.
    - Start directly with the text (do not include the title in the very first line as an H1, I will handle the title).
    - Use clear headings (H2, H3), bullet points, and short paragraphs.
    - The tone should be engaging, informative, and authoritative.
    - Provide deep insights, not just superficial facts. Make it feel authentic, not like AI.
    - Word count: ~600-800 words.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating content with Gemini: {e}")
        return None

def save_to_github_jekyll(title, content):
    """Save the content as a markdown file in the _posts folder for Jekyll."""
    print(f"Saving article: {title}")
    
    # Create _posts directory if it doesn't exist
    if not os.path.exists('_posts'):
        os.makedirs('_posts')
        
    date_str = datetime.now().strftime('%Y-%m-%d')
    # Clean title for filename
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    filename = f"{date_str}-{clean_title.strip().replace(' ', '-').lower()}.md"
    filepath = os.path.join('_posts', filename)
    
    # Check if file already exists to prevent duplicates
    if os.path.exists(filepath):
        print(f"File {filepath} already exists. Skipping.")
        return
        
    # Jekyll Front Matter
    front_matter = f"""---
layout: post
title: "{title}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}
categories: [Trends, USA]
---

"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter + content)
    print(f"Successfully saved to {filepath}")

if __name__ == "__main__":
    trends = get_us_trends()
    if not trends:
        print("No trends found. Exiting.")
        exit()
        
    for trend in trends: # Generate an article for the top trend
        article_content = ask_gemini(trend)
        if article_content:
            save_to_github_jekyll(trend, article_content)
            print("Finished processing one trend. Pausing for a moment to respect API limits.")
            time.sleep(10) # Pause between generation
            break # Let's just do 1 per run to start with
