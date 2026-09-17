import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TwitterMonitor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.twitterapi.io/v1"
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def get_handle_from_url(self, url):
        """Extract handle from X.com URL"""
        if "x.com/" in url:
            return url.split("x.com/")[-1].strip("/")
        return url.strip("@")
    
    def get_user_tweets(self, handle, max_results=5):
        """Fetch recent tweets from a handle"""
        try:
            endpoint = f"{self.base_url}/tweets/search/recent"
            params = {
                "query": f"from:{handle}",
                "max_results": max_results,
                "tweet.fields": "created_at,public_metrics"
            }
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching tweets for {handle}: {e}")
            return []
    
    def get_latest_tweet(self, handle):
        """Get the most recent tweet from a handle"""
        tweets = self.get_user_tweets(handle, max_results=1)
        if tweets:
            return tweets[0]
        return None
    
    def format_tweet(self, tweet):
        """Format tweet for Telegram"""
        text = tweet.get("text", "")
        created_at = tweet.get("created_at", "")
        metrics = tweet.get("public_metrics", {})
        
        formatted = (
            f"<b>Tweet</b>\n\n"
            f"{text}\n\n"
            f"<i>Likes: {metrics.get('like_count', 0)} | "
            f"Retweets: {metrics.get('retweet_count', 0)} | "
            f"Replies: {metrics.get('reply_count', 0)}</i>\n\n"
            f"<i>{created_at}</i>"
        )
        return formatted
