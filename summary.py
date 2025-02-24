import os
import sys
import re
from huggingface_hub import InferenceClient

# Check for input file argument
if len(sys.argv) > 1:
    input_path = sys.argv[1]
else:
    print("Usage: python LLM_Summary.py <input_file>")
    sys.exit(1)

# Configuration for the LLM summarizer
API_KEY = "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"  # Replace with your Hugging Face API token if needed
model = "mistralai/Mistral-7B-Instruct-v0.3"

client = InferenceClient(model=model, token=API_KEY)

# ==============================
# 1. Import necessary libraries
# ==============================
try:
    import pdfplumber
except ImportError:
    print("Please install pdfplumber: pip install pdfplumber")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install sentence-transformers: pip install sentence-transformers")
    sys.exit(1)

# ==========================
# 2. Text Extraction
# ==========================
def extract_text(input_path):
    """
    Extracts text from a PDF using pdfplumber if the file ends with '.pdf',
    otherwise reads the file as plain text.
    """
    text = ""
    if input_path.lower().endswith(".pdf"):
        try:
            with pdfplumber.open(input_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            sys.exit(1)
    else:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading text file: {e}")
            sys.exit(1)
    return text

# ==========================
# 3. Compute Relevance, Novelty & Heat Scores
# ==========================
def compute_relevance_score(text, keywords):
    """Computes relevance based on keyword matching and embedding similarity."""
    text_lower = text.lower()
    keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    similarity_score = len(set(text_lower.split()) & set(keywords)) / len(set(text_lower.split()))
    return (keyword_matches * 2 + similarity_score * 10) / (len(keywords) + 1) * 100

def compute_novelty_score(text):
    """Computes a novelty score using LLM analysis."""
    prompt = f"""
    You are an AI expert in technological innovation. Given the following text, analyze how novel the described technology is.
    Please rate novelty from 0 to 100, where:
    - 0 means the technology is widely known and mature
    - 100 means the technology is groundbreaking and recently emerging
    Here is the text:
    {text}
    Give me a score and also give a single line explaination why it is novel or not.
    """
    return client.text_generation(prompt, max_new_tokens=512).strip()

def compute_heat_score(text):
    """Computes a heat score based on industry adoption and recurrence."""
    prompt = f"""
    You are an AI expert in tracking technology trends. Based on the following text, determine how popular and widely adopted the described technology is in the industry.
    Please rate the heat score from 0 to 100, where:
    - 0 means the technology is niche and rarely mentioned
    - 100 means the technology is widely adopted and frequently discussed
    Here is the text:
    {text}
    Give me a score and also give a single line explaination why it is hot or not.
    """
    return client.text_generation(prompt, max_new_tokens=512).strip()

# ==========================
# 4. Summarization
# ==========================
def summarize_with_llm(text):
    """Summarizes the text using an LLM with a detailed and structured prompt."""
    prompt = f"""
    You are an advanced AI model specializing in analyzing and summarizing articles related to technology, innovation, and industry trends. 
    Your task is to generate a concise and informative summary that captures the key points and insights from the provided text. 
    Ensure that the summary highlights major advancements, industry impact, and relevance to emerging trends. And this is for ADNOC's strategic needs.
    
    Here is the full article text:
    {text}
    
    "Please provide a concise overview of the key technologies, innovations, and any forecasts mentioned, focusing on ADNOC's strategic needs."
    Please provide a well-structured summary in bullet points, focusing on:
    - Core technological innovations
    - Industry impact and relevance
    - Future implications and trends
    - ADNOC's strategic alignment and potential opportunities

    Also provide me with the latest companies/startups which are working on these technologies/innovations, especially in the Oil and Gas field. Don't repeat companies and exclude obvious/big/famous ones.
    """
    return client.text_generation(prompt, max_new_tokens=1024)

# ==========================
# 5. Main Execution
# ==========================
if __name__ == "__main__":
    input_text = extract_text(input_path)
    if not input_text.strip():
        print("No text found in the input file. Exiting.")
        sys.exit(1)
    
    summary = summarize_with_llm(input_text)
    relevance_score = compute_relevance_score(input_text, ["AI", "machine learning", "energy", "ESG", "sustainability", "oil", "gas"])
    novelty_score = compute_novelty_score(input_text)
    heat_score = compute_heat_score(input_text)
    
    print("SUMMARY:", summary)
    print("RELEVANCE SCORE:", relevance_score)
    print("NOVELTY SCORE:", novelty_score)
    print("HEAT SCORE:", heat_score)