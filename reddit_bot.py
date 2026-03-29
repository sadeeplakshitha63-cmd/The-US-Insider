import os
import praw
import google.generativeai as genai

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = "windows:TheUSInsiderBot:v1.0 (by /u/YourRedditUsername)"
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD")

genai.configure(api_key=GEMINI_API_KEY)

def generate_reply(question):
    print("Drafting an answer using Gemini...")
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    # Crucial Prompt: 80% Value, 20% promotion. Sound human!
    prompt = f"""
    A Reddit user asked: "{question}"
    
    Write a helpful, insightful, and human-like response (around 3-4 paragraphs).
    Provide genuine value, facts, or helpful suggestions. Do not sound like an AI bot.
    At the very end, naturally include a brief mention: "For more deeper insights on US tech and trends, check out my site [The US Insider](https://your-site-url.github.io)."
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

def monitor_reddit():
    print("Connecting to Reddit...")
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD
    )

    # Subreddits to monitor
    subreddits = ['technology', 'finance', 'ask']
    for sub in subreddits:
        print(f"Checking r/{sub} for new questions...")
        subreddit = reddit.subreddit(sub)
        
        # Look at the latest submissions (limit 5)
        for submission in subreddit.new(limit=5):
            # Check if it looks like a question
            if "?" in submission.title:
                print(f"Found Question: {submission.title}")
                
                # IMPORTANT: Automatically replying on Reddit can lead to bans quickly. 
                # This script is generating the text, but it's highly recommended to 
                # review it manually before actually sending `submission.reply(reply_text)`
                
                reply_text = generate_reply(submission.title)
                if reply_text:
                    print("--- Generated Reply ---")
                    print(reply_text)
                    print("-----------------------\n")
                    
                    # UNCOMMENT THIS ONLY IF YOU WANT TO DANGEROUSLY AUTO-REPLY
                    # submission.reply(reply_text)
                    # print("Replied to Reddit thread!")
                    
if __name__ == "__main__":
    monitor_reddit()
