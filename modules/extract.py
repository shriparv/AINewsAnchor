from newspaper import Article

def extract_text(url):
    try:
        art = Article(url)
        art.download()
        art.parse()
        return art.text[:5000]  # limit
    except:
        return ""