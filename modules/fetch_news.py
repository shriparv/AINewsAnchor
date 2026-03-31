import requests
from config import NEWS_API_KEY, NUM_ARTICLES

def fetch_articles():
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "category": "technology",
       # "q": "technology OR hardware OR software OR Cloud technology OR quantum computing OR machine learning OR artificial intelligence OR neural network OR deep learning ",
        "language": "en",
       # "sortBy": "relevance",
        "sortBy": "publishedAt",
        "pageSize": NUM_ARTICLES,
        "apiKey": NEWS_API_KEY
    }
    res = requests.get(url, params=params).json()
    return res.get("articles", [])  