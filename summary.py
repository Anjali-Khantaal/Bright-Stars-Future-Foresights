"""
LLM_Summary.py

A script that:
1) Extracts text from a PDF using pdfplumber or reads text from a plain text file
2) Splits text into manageable chunks
3) Creates embeddings of chunks using a SentenceTransformer model
4) Stores embeddings in a FAISS vector index
5) Retrieves the most relevant chunks for a user query
6) Summarizes those chunks with a local open-source LLM (Falcon-7B-Instruct)
"""

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

def compute_relevance_score(text, keywords):
    """Computes relevance based on keyword matching and embedding similarity."""
    text_lower = text.lower()
    keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    similarity_score = len(set(text_lower.split()) & set(keywords)) / len(set(text_lower.split()))
    return (keyword_matches * 2 + similarity_score * 10) / (len(keywords) + 1) * 100

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

    Also provide me with the latest companies/startups which are working on these technologies/innovations specially in the Oil and Gas field. Don't repeat the companies and not the obvious/big/famous ones.
    """
    return client.text_generation(prompt, max_new_tokens=1024)

if __name__ == "__main__":
    input_text = extract_text(input_path)
    if not input_text.strip():
        print("No text found in the input file. Exiting.")
        sys.exit(1)
    
    summary = summarize_with_llm(input_text)
    relevance_score = compute_relevance_score(input_text, ["AI", "machine learning", "energy", "ESG", "sustainability", "oil", "gas"])
    
    print("SUMMARY:", summary)
    print("RELEVANCE SCORE:", relevance_score)
