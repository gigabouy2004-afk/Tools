import feedparser
import pandas as pd
import re
import urllib.request
import urllib.parse
import sys
import calendar
import time

def fetch_free_consolidated_news(ticker):
    try:
        raw_query = f"{ticker} (stock OR finance OR earnings OR market OR compliance) -politics -government -election"
        encoded_query = urllib.parse.quote(raw_query)
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            raw_data = response.read().decode('utf-8', errors='ignore')
            
        feed = feedparser.parse(raw_data)
        extracted_articles = []
        
        current_epoch = time.time()
        two_days_seconds = 2 * 24 * 60 * 60
        
        political_blacklist = ['politics', 'government', 'election', 'senate', 'congress', 'white house', 'lawmaker']
        
        for entry in feed.entries:
            time_struct = entry.get('published_parsed', entry.get('updated_parsed', None))
            if time_struct:
                entry_epoch = calendar.timegm(time_struct)
                if (current_epoch - entry_epoch) > two_days_seconds:
                    continue
            else:
                continue
                
            heading = entry.get('title', '').strip()
            raw_paragraph = entry.get('summary', entry.get('description', ''))
            clean_paragraph = re.sub(r'<[^>]+>', '', raw_paragraph).strip()
            
            combined_text = f"{heading} {clean_paragraph}".lower()
            if any(term in combined_text for term in political_blacklist):
                continue
                
            date_stamp = entry.get('published', entry.get('updated', '')).strip()
            provider_name = entry.get('source', {}).get('title', 'Unknown Provider').strip()
            
            if heading and clean_paragraph:
                extracted_articles.append({
                    'Provider': provider_name,
                    'Heading': heading,
                    'Date': date_stamp,
                    'Paragraph': clean_paragraph
                })
                
        df = pd.DataFrame(extracted_articles)
        
        # Deduplicate the DataFrame to retain exactly 1 top news entry per unique Provider
        if not df.empty:
            df = df.drop_duplicates(subset=['Provider'], keep='first').reset_index(drop=True)
            
        return df
        
    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Missing stock code argument. Usage: python script.py -STOCKCODE")
        sys.exit(1)
        
    cli_argument = sys.argv[1]
    sample_keyword = cli_argument.lstrip('-').upper()
    
    sentiment_input_df = fetch_free_consolidated_news(sample_keyword)
    
    if not sentiment_input_df.empty:
        for index, row in sentiment_input_df.iterrows():
            print(f"PROVIDER: {row['Provider']}")
            print(f"HEADING: {row['Heading']}")
            print(f"DATE: {row['Date']}")
            print(f"PARAGRAPH: {row['Paragraph']}")
            print("-" * 100)
    else:
        print(f"No specific financial entries found from the last 2 days for '{sample_keyword}'.")