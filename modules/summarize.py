import requests
import re


def clean_output(text: str) -> str:
    """Cleans raw LLM output into readable, normalized summary text."""

    # Strip leading/trailing whitespace
    text = text.strip()

    # Remove common intro lines like "Here is a summary:", "Summary:", etc.
    text = re.sub(r"(?im)^.*\b(summary|summarize|here is|here's|below is)\b.*:\s*", "", text)

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


def summarize(text: str) -> str:
    """
    Summarizes input text into ~5 concise sentences using Llama3 via Ollama.

    Args:
        text: The input text to summarize.
    Returns:
        A cleaned, concise summary string.
    Raises:
        ValueError: If input or model response is empty.
        RuntimeError: On connection, timeout, or HTTP errors.
    """

    if not text or not text.strip():
        raise ValueError("Input text is empty or blank.")

    prompt = f"""You are a precise news summarization assistant.

Summarize the following text into exactly 2 or 3 short, conversational sentences.
- DO NOT use bullet points or lists.
- Do not add opinions, intros, or extra commentary.
- Just output the explanation paragraph directly.

Text:
\"\"\"
{text.strip()}
\"\"\"

Summary:"""

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,   # Lower = focused, factual output
                    "top_p": 0.9,
                    "num_predict": 300,   # Cap output length
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