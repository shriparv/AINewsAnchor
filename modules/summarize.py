import requests
import re


def clean_output(text: str) -> str:
    """Cleans raw LLM output into readable, normalized summary text."""

    # Strip leading/trailing whitespace
    text = text.strip()

    # Remove common intros that start with "Summary:" or "Here is..." if they look like metadata
    text = re.sub(r"(?im)^(Summary|Summarize):\s*", "", text)

    # Remove markdown bold/italic markers (** or *)
    text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", text)

    # Remove special/non-printable characters (keep basic punctuation + bullets)
    text = re.sub(r"[^\w\s.,!\?;:\-•\(\)]", "", text)

    # Normalize bullet variants to dash
    text = re.sub(r"^[\•\-\*]\s*", "- ", text, flags=re.MULTILINE)

    # Remove numbered list artifacts like "1." "2." at line start
    text = re.sub(r"^\d+\.\s*", "", text, flags=re.MULTILINE)

    # Collapse multiple spaces into one
    text = re.sub(r"  +", " ", text)

    # Remove extra blank lines, strip each line
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

    return text


from config import LLM_MODEL

def summarize(title: str, text: str) -> str:
    """
    Summarizes input text into ~5 concise sentences using the local LLM.

    Args:
        title: The news topic or headline.
        text: The input text to summarize.
    Returns:
        A cleaned, concise summary string.
    Raises:
        ValueError: If input or model response is empty.
        RuntimeError: On connection, timeout, or HTTP errors.
    """

    if not text or not text.strip():
        raise ValueError("Input text is empty or blank.")

    prompt = f"""You are an expert news editor. Your task is to write a clean, high-quality summary of the provided news article.

STRICT STYLE RULES:
- Write a concise, factual, and professional news summary.
- Focus ONLY on the core facts and key takeaways.
- Keep it concise: exactly 2–4 short sentences.
- NEVER use conversational filler, introductions, greetings, or meta-commentary (e.g., NEVER say "Here is the summary", "Good evening", or "I'm your host").
- No bullet points, no lists.
- Begin immediately with the news fact.

News Topic:
{title}

News Body:
\"\"\"
{text.strip()}
\"\"\"

News Summary:"""

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.6,   # Higher = more organic, varied phrasing
                    "top_p": 0.9,
                    "num_predict": 400,   # Increased space for storytelling
                }
            },
            timeout=60
        )
        res.raise_for_status()

    except requests.exceptions.Timeout:
        raise RuntimeError("Request timed out. Ollama may be overloaded.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to Ollama. Is it running on localhost:11434?")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama returned an HTTP error: {e}")

    raw_output = res.json().get("response", "").strip()

    if not raw_output:
        raise ValueError("Model returned an empty response.")

    return clean_output(raw_output)


def generate_video_metadata(news_summary_text: str):
    """Generates a catchy YouTube title and SEO tags based on all processed news."""
    
    prompt = f"""You are an expert YouTube SEO strategist.
    Based on the following news headlines and summaries, generate:
    1. A single "hook" style YouTube title (max 100 chars, no quotes).
    2. A list of 20-30 comma-separated SEO keywords (tags).
    
    Format your response EXACTLY like this:
    TITLE: [Insert catchy title here]
    TAGS: [tag1, tag2, tag3, ...]
    
    News Content:
    \"\"\"
    {news_summary_text}
    \"\"\"
    
    Metadata:"""

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.5, "num_predict": 400}
            },
            timeout=60
        )
        res.raise_for_status()
        raw = res.json().get("response", "").strip()
        
        # Simple parsing
        title = "Daily AI Tech News Update"
        tags = []
        
        for line in raw.splitlines():
            if line.upper().startswith("TITLE:"):
                title = line[6:].strip().strip('[]"')
            elif line.upper().startswith("TAGS:"):
                # Clean up the comma-separated tags
                tags_raw = line[5:].strip().strip('[]"')
                tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

        return title, tags
    except Exception as e:
        print(f"⚠️ Metadata generation failed: {e}")
        return "Daily AI Tech News Update", ["TechNews", "Technology", "AINews"]
