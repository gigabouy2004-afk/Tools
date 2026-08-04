import feedparser
import pandas as pd
import re
import urllib.request

def fetch_ticker_rss_for_sentiment(ticker):
    try:
        feed_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        }
        
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            raw_data = response.read().decode('utf-8', errors='ignore')
        
        feed = feedparser.parse(raw_data)
        extracted_articles = []
        
        for entry in feed.entries:
            heading = entry.get('title', '').strip()
            
            # Extract the date stamp (falls back to 'updated' if 'published' is missing)
            date_stamp = entry.get('published', entry.get('updated', '')).strip()
            
            raw_paragraph = entry.get('summary', entry.get('description', ''))
            clean_paragraph = re.sub(r'<[^>]+>', '', raw_paragraph).strip()
            
            if heading and clean_paragraph:
                extracted_articles.append({
                    'Heading': heading,
                    'Date': date_stamp,
                    'Paragraph': clean_paragraph
                })
        
        df = pd.DataFrame(extracted_articles)
        return df
        
    except Exception as e:
        print(f"An error occurred while parsing the RSS feed for {ticker}: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    sample_keyword = "PLUG"
    
    sentiment_input_df = fetch_ticker_rss_for_sentiment(sample_keyword)
    
    if not sentiment_input_df.empty:
        for index, row in sentiment_input_df.iterrows():
            print(f"HEADING: {row['Heading']}")
            print(f"DATE: {row['Date']}")
            print(f"PARAGRAPH: {row['Paragraph']}")
            print("-" * 100)
    else:
        print(f"DataFrame is empty. Yahoo's structural server-side block prevents data retrieval from this URL.")