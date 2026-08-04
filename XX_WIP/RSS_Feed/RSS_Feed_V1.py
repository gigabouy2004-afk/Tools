import urllib.request
import xml.etree.ElementTree as ET

def get_ddog_headlines():
    # Yahoo Finance RSS feed for DDOG
    url = "https://finance.yahoo.com/rss/headline?s=DDOG"
    try:
        # Standard User-Agent header to prevent HTTP 403 blocks
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        print("--- Latest Datadog (DDOG) News Headlines ---")
        
        # Parse and print the top 5 articles
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            pub_date = item.find('pubDate').text
            print(f"[{pub_date}]\n{title}\n")
            
    except Exception as e:
        print(f"Could not retrieve headlines: {e}")

if __name__ == "__main__":
    get_ddog_headlines()