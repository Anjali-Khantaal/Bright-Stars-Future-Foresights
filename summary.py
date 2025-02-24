"""
Enhanced LLM_Summary.py

A script that:
1) Extracts text from PDFs and plain text files
2) Provides comprehensive text analysis including:
    - Relevance scoring
    - Novelty scoring
    - Heat/trending scoring
3) Generates structured summaries using Mistral-7B
4) Integrates with the article collection and dashboard systems
"""

import os
import sys
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from huggingface_hub import InferenceClient
import numpy as np
from sentence_transformers import SentenceTransformer
import pdfplumber
from collections import Counter

# Configuration
API_KEY = "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"
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

@dataclass
class TextAnalysis:
    summary: str
    relevance_score: float
    novelty_score: float
    heat_score: float
    companies: List[str]
    technologies: List[str]

class TextProcessor:
    def __init__(self):
        self.client = InferenceClient(model=MODEL_NAME, token=API_KEY)
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Keywords for different aspects of analysis
        self.innovation_indicators = {
            'breakthrough': 10,
            'revolutionary': 8,
            'first-ever': 10,
            'innovative': 7,
            'novel': 6,
            'patent': 7,
            'prototype': 5,
            'research': 4
        }
        
        self.trending_indicators = {
            'trending': 10,
            'viral': 9,
            'popular': 7,
            'breaking': 8,
            'exclusive': 6,
            'announces': 5,
            'launches': 6
        }
        
        self.relevance_keywords = [
            "AI", "machine learning", "energy", "ESG", "sustainability", 
            "oil", "gas", "renewable", "digital", "automation"
        ]

    def extract_text(self, input_path: str) -> str:
        """Enhanced text extraction with better error handling."""
        try:
            if input_path.lower().endswith(".pdf"):
                with pdfplumber.open(input_path) as pdf:
                    text = "\n".join(
                        page.extract_text() for page in pdf.pages 
                        if page.extract_text()
                    )
            else:
                with open(input_path, "r", encoding="utf-8") as f:
                    text = f.read()
            
            # Clean and normalize text
            text = re.sub(r'\s+', ' ', text).strip()
            return text if text else None
            
        except Exception as e:
            print(f"Error processing file {input_path}: {e}")
            return None

    def compute_relevance_score(self, text: str) -> float:
        """Enhanced relevance scoring using multiple factors."""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        # Keyword matching
        keyword_matches = sum(1 for kw in self.relevance_keywords if kw.lower() in text_lower)
        
        # Semantic similarity using embeddings
        text_embedding = self.embedding_model.encode([text_lower])[0]
        keywords_embedding = self.embedding_model.encode([' '.join(self.relevance_keywords)])[0]
        semantic_similarity = np.dot(text_embedding, keywords_embedding) / (
            np.linalg.norm(text_embedding) * np.linalg.norm(keywords_embedding)
        )
        
        # Combine scores with weights
        combined_score = (
            0.4 * (keyword_matches / len(self.relevance_keywords) * 100) +
            0.6 * (semantic_similarity * 100)
        )
        
        return min(100, max(0, combined_score))

    def compute_novelty_score(self, text: str) -> float:
        """Calculate novelty score based on innovation indicators."""
        text_lower = text.lower()
        score = 0
        total_weight = 0
        
        # Check for innovation indicators
        for indicator, weight in self.innovation_indicators.items():
            if indicator in text_lower:
                score += weight
                total_weight += weight
        
        # Check for technical terminology density
        technical_terms = re.findall(r'\b(?:[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*)\b', text)
        technical_density = len(technical_terms) / len(text.split())
        
        # Check for numbers and measurements (often indicating technical content)
        measurements = len(re.findall(r'\d+(?:\.\d+)?(?:\s*[A-Za-z]+)?', text))
        
        combined_score = (
            0.5 * (score / max(total_weight, 1) * 100) +
            0.3 * (technical_density * 100) +
            0.2 * min(100, measurements * 5)
        )
        
        return min(100, max(0, combined_score))

    def compute_heat_score(self, text: str) -> float:
        """Calculate heat score based on trending indicators."""
        text_lower = text.lower()
        score = 0
        total_weight = 0
        
        # Check for trending indicators
        for indicator, weight in self.trending_indicators.items():
            if indicator in text_lower:
                score += weight
                total_weight += weight
        
        # Check for temporal indicators
        recent_time_indicators = ['today', 'this week', 'this month', 'recently', 'just announced']
        temporal_score = sum(5 for indicator in recent_time_indicators if indicator in text_lower)
        
        # Check for social media and engagement indicators
        engagement_indicators = ['viral', 'trending', 'popular', 'widely adopted', 'industry standard']
        engagement_score = sum(8 for indicator in engagement_indicators if indicator in text_lower)
        
        combined_score = (
            0.4 * (score / max(total_weight, 1) * 100) +
            0.3 * min(100, temporal_score * 10) +
            0.3 * min(100, engagement_score * 10)
        )
        
        return min(100, max(0, combined_score))

    def extract_companies_and_technologies(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract mentioned companies and technologies."""
        # Company extraction pattern
        company_pattern = r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Ltd|LLC|Corp|Corporation|Company))?)'
        companies = re.findall(company_pattern, text)
        
        # Technology extraction pattern
        tech_pattern = r'(?:[A-Z][a-z]*(?:\s*[A-Z][a-z]+)*(?:\s+(?:technology|system|platform|solution|algorithm))?)'
        technologies = re.findall(tech_pattern, text)
        
        return list(set(companies)), list(set(technologies))

    def summarize_with_llm(self, text: str) -> str:
        """Enhanced summarization with structured output."""
        prompt = f"""
        You are an advanced AI model specializing in analyzing and summarizing articles related to technology, innovation, and industry trends. 
        Your task is to generate a detailed summary for ADNOC's strategic needs.
        
        Article text:
        {text}
        
        Please provide a comprehensive analysis in the following format:

        CORE INNOVATIONS:
        - [List key technological innovations and advancements]

        INDUSTRY IMPACT:
        - [Analyze impact on oil & gas industry]
        - [Discuss market implications]

        STRATEGIC OPPORTUNITIES:
        - [Identify opportunities for ADNOC]
        - [Highlight potential applications]

        EMERGING PLAYERS:
        - [List relevant emerging companies/startups]
        - [Focus on non-obvious players]
        """
        
        return self.client.text_generation(prompt, max_new_tokens=1024, temperature=0.7)

    def analyze_text(self, text: str) -> TextAnalysis:
        """Perform comprehensive text analysis."""
        summary = self.summarize_with_llm(text)
        relevance_score = self.compute_relevance_score(text)
        novelty_score = self.compute_novelty_score(text)
        heat_score = self.compute_heat_score(text)
        companies, technologies = self.extract_companies_and_technologies(text)
        
        return TextAnalysis(
            summary=summary,
            relevance_score=relevance_score,
            novelty_score=novelty_score,
            heat_score=heat_score,
            companies=companies,
            technologies=technologies
        )

def main():
    if len(sys.argv) < 2:
        print("Usage: python LLM_Summary.py <input_file>")
        sys.exit(1)

    processor = TextProcessor()
    input_text = processor.extract_text(sys.argv[1])
    
    if not input_text:
        print("No text found in the input file. Exiting.")
        sys.exit(1)
    
    analysis = processor.analyze_text(input_text)
    
    # Print results in the format expected by the article collector
    print("SUMMARY:", analysis.summary)
    print("RELEVANCE SCORE:", analysis.relevance_score)
    print("NOVELTY SCORE:", analysis.novelty_score)
    print("HEAT SCORE:", analysis.heat_score)

if __name__ == "__main__":
    main()

# """
# Enhanced LLM_Summary.py

# A script that:
# 1) Extracts text from PDFs and plain text files
# 2) Provides comprehensive text analysis including:
#     - Relevance scoring
#     - Novelty scoring
#     - Heat/trending scoring
# 3) Generates structured summaries using Mistral-7B
# 4) Integrates with the article collection and dashboard systems
# """

# import os
# import sys
# import re
# from typing import Dict, List, Tuple, Optional
# from dataclasses import dataclass
# from datetime import datetime
# import json
# from huggingface_hub import InferenceClient
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import pdfplumber
# from collections import Counter

# # Configuration
# API_KEY = "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"
# MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
# EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# MAX_TOKENS = 4096  # Maximum tokens Mistral-7B can handle
# SUMMARY_LENGTH = 300  # Target length for the summary

# @dataclass
# class TextAnalysis:
#     summary: str
#     relevance_score: float
#     novelty_score: float
#     heat_score: float
#     companies: List[str]
#     technologies: List[str]

# class TextProcessor:
#     def __init__(self):
#         self.client = InferenceClient(model=MODEL_NAME, token=API_KEY)
#         self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
#         # Keywords for different aspects of analysis
#         self.innovation_indicators = {
#             'breakthrough': 10,
#             'revolutionary': 8,
#             'first-ever': 10,
#             'innovative': 7,
#             'novel': 6,
#             'patent': 7,
#             'prototype': 5,
#             'research': 4
#         }
        
#         self.trending_indicators = {
#             'trending': 10,
#             'viral': 9,
#             'popular': 7,
#             'breaking': 8,
#             'exclusive': 6,
#             'announces': 5,
#             'launches': 6
#         }
        
#         self.relevance_keywords = [
#             "AI", "machine learning", "energy", "ESG", "sustainability", 
#             "oil", "gas", "renewable", "digital", "automation"
#         ]

#     def extract_text(self, input_path: str) -> str:
#         """Enhanced text extraction with better error handling."""
#         try:
#             if input_path.lower().endswith(".pdf"):
#                 with pdfplumber.open(input_path) as pdf:
#                     text = "\n".join(
#                         page.extract_text() for page in pdf.pages 
#                         if page.extract_text()
#                     )
#             else:
#                 with open(input_path, "r", encoding="utf-8") as f:
#                     text = f.read()
            
#             # Clean and normalize text
#             text = re.sub(r'\s+', ' ', text).strip()
#             return text if text else None
            
#         except Exception as e:
#             print(f"Error processing file {input_path}: {e}")
#             return None

#     def preprocess_text(self, text: str) -> str:
#         """Preprocess text to ensure it's within token limits."""
#         # Truncate text to fit within the model's token limit
#         words = text.split()
#         if len(words) > MAX_TOKENS:
#             text = " ".join(words[:MAX_TOKENS])
#         return text

#     def compute_relevance_score(self, text: str) -> float:
#         """Enhanced relevance scoring using multiple factors."""
#         text_lower = text.lower()
#         words = set(text_lower.split())
        
#         # Keyword matching
#         keyword_matches = sum(1 for kw in self.relevance_keywords if kw.lower() in text_lower)
        
#         # Semantic similarity using embeddings
#         text_embedding = self.embedding_model.encode([text_lower])[0]
#         keywords_embedding = self.embedding_model.encode([' '.join(self.relevance_keywords)])[0]
#         semantic_similarity = np.dot(text_embedding, keywords_embedding) / (
#             np.linalg.norm(text_embedding) * np.linalg.norm(keywords_embedding)
#         )
        
#         # Combine scores with weights
#         combined_score = (
#             0.4 * (keyword_matches / len(self.relevance_keywords) * 100) +
#             0.6 * (semantic_similarity * 100)
#         )
        
#         return min(100, max(0, combined_score))

#     def compute_novelty_score(self, text: str) -> float:
#         """Calculate novelty score based on innovation indicators."""
#         text_lower = text.lower()
#         score = 0
#         total_weight = 0
        
#         # Check for innovation indicators
#         for indicator, weight in self.innovation_indicators.items():
#             if indicator in text_lower:
#                 score += weight
#                 total_weight += weight
        
#         # Check for technical terminology density
#         technical_terms = re.findall(r'\b(?:[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*)\b', text)
#         technical_density = len(technical_terms) / len(text.split())
        
#         # Check for numbers and measurements (often indicating technical content)
#         measurements = len(re.findall(r'\d+(?:\.\d+)?(?:\s*[A-Za-z]+)?', text))
        
#         combined_score = (
#             0.5 * (score / max(total_weight, 1) * 100) +
#             0.3 * (technical_density * 100) +
#             0.2 * min(100, measurements * 5)
#         )
        
#         return min(100, max(0, combined_score))

#     def compute_heat_score(self, text: str) -> float:
#         """Calculate heat score based on trending indicators."""
#         text_lower = text.lower()
#         score = 0
#         total_weight = 0
        
#         # Check for trending indicators
#         for indicator, weight in self.trending_indicators.items():
#             if indicator in text_lower:
#                 score += weight
#                 total_weight += weight
        
#         # Check for temporal indicators
#         recent_time_indicators = ['today', 'this week', 'this month', 'recently', 'just announced']
#         temporal_score = sum(5 for indicator in recent_time_indicators if indicator in text_lower)
        
#         # Check for social media and engagement indicators
#         engagement_indicators = ['viral', 'trending', 'popular', 'widely adopted', 'industry standard']
#         engagement_score = sum(8 for indicator in engagement_indicators if indicator in text_lower)
        
#         combined_score = (
#             0.4 * (score / max(total_weight, 1) * 100) +
#             0.3 * min(100, temporal_score * 10) +
#             0.3 * min(100, engagement_score * 10)
#         )
        
#         return min(100, max(0, combined_score))

#     def extract_companies_and_technologies(self, text: str) -> Tuple[List[str], List[str]]:
#         """Extract mentioned companies and technologies."""
#         # Company extraction pattern
#         company_pattern = r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Ltd|LLC|Corp|Corporation|Company))?)'
#         companies = re.findall(company_pattern, text)
        
#         # Technology extraction pattern
#         tech_pattern = r'(?:[A-Z][a-z]*(?:\s*[A-Z][a-z]+)*(?:\s+(?:technology|system|platform|solution|algorithm))?)'
#         technologies = re.findall(tech_pattern, text)
        
#         return list(set(companies)), list(set(technologies))

#     def summarize_with_llm(self, text: str) -> str:
#         """Enhanced summarization with structured output."""
#         prompt = f"""
#         You are an advanced AI model specializing in analyzing and summarizing articles related to technology, innovation, and industry trends. 
#         Your task is to generate a detailed summary for ADNOC's strategic needs.
        
#         Article text:
#         {text}
        
#         Please provide a comprehensive analysis in the following format:

#         CORE INNOVATIONS:
#         - [List key technological innovations and advancements]

#         INDUSTRY IMPACT:
#         - [Analyze impact on oil & gas industry]
#         - [Discuss market implications]

#         STRATEGIC OPPORTUNITIES:
#         - [Identify opportunities for ADNOC]
#         - [Highlight potential applications]

#         EMERGING PLAYERS:
#         - [List relevant emerging companies/startups]
#         - [Focus on non-obvious players]
#         """
        
#         try:
#             # Preprocess text to fit within token limits
#             text = self.preprocess_text(text)
            
#             # Generate summary using Mistral-7B
#             summary = self.client.text_generation(prompt, max_new_tokens=SUMMARY_LENGTH, temperature=0.7)
#             return summary
#         except Exception as e:
#             print(f"Error generating summary: {e}")
#             return f"Error: {e}"

#     def analyze_text(self, text: str) -> TextAnalysis:
#         """Perform comprehensive text analysis."""
#         try:
#             text = self.preprocess_text(text)
#             summary = self.summarize_with_llm(text)
#             relevance_score = self.compute_relevance_score(text)
#             novelty_score = self.compute_novelty_score(text)
#             heat_score = self.compute_heat_score(text)
#             companies, technologies = self.extract_companies_and_technologies(text)
            
#             return TextAnalysis(
#                 summary=summary,
#                 relevance_score=relevance_score,
#                 novelty_score=novelty_score,
#                 heat_score=heat_score,
#                 companies=companies,
#                 technologies=technologies
#             )
#         except Exception as e:
#             print(f"Error analyzing text: {e}")
#             return TextAnalysis(
#                 summary=f"Error: {e}",
#                 relevance_score=0.0,
#                 novelty_score=0.0,
#                 heat_score=0.0,
#                 companies=[],
#                 technologies=[]
#             )

# def main():
#     if len(sys.argv) < 2:
#         print("Usage: python LLM_Summary.py <input_file>")
#         sys.exit(1)

#     processor = TextProcessor()
#     input_text = processor.extract_text(sys.argv[1])
    
#     if not input_text:
#         print("No text found in the input file. Exiting.")
#         sys.exit(1)
    
#     analysis = processor.analyze_text(input_text)
    
#     # Print results in the format expected by the article collector
#     print("SUMMARY:", analysis.summary)
#     print("RELEVANCE SCORE:", analysis.relevance_score)
#     print("NOVELTY SCORE:", analysis.novelty_score)
#     print("HEAT SCORE:", analysis.heat_score)

# if __name__ == "__main__":
#     main()

# """
# LLM_Summary.py

# A script that:
# 1) Extracts text from a PDF (using pdfplumber) or reads text from a plain text file.
# 2) Splits text into manageable chunks.
# 3) Creates embeddings of chunks using a SentenceTransformer model.
# 4) Stores embeddings in a FAISS vector index.
# 5) Retrieves the most relevant chunks for a user query.
# 6) Summarizes those chunks with a local open‑source LLM (Falcon‑7B‑Instruct).
# 7) Computes:
#     - A relevance score (based on keyword matching).
#     - A novelty score (using LLM knowledge to assess how innovative the technology is).
#     - A heat score (by comparing the technology against other articles in a database).
# """

# import os
# import sys
# import re
# import sqlite3
# from datetime import datetime

# from huggingface_hub import InferenceClient

# # Configuration for the LLM summarizer
# API_KEY = "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"  # Replace with your Hugging Face API token if needed
# MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
# client = InferenceClient(model=MODEL, token=API_KEY)

# # Database filename (should match the one in your fetching script)
# DATABASE = "articles.db"

# try:
#     import pdfplumber
# except ImportError:
#     print("Please install pdfplumber: pip install pdfplumber")
#     sys.exit(1)

# try:
#     from sentence_transformers import SentenceTransformer
# except ImportError:
#     print("Please install sentence-transformers: pip install sentence-transformers")
#     sys.exit(1)

# # Use the same TECHNOLOGY_KEYWORDS as in your fetching script for consistency.
# TECHNOLOGY_KEYWORDS = [
#     # General Oil & Gas Industry Terms
#     "oil", "gas", "petroleum",
 
#     # Digital Transformation & Automation
#     "technology", "innovation", "AI", "machine learning", "automation",
#     "robotics", "digital transformation", "IoT", "sustainability",
#     "digital twin", "predictive analytics", "edge computing", "cloud computing",
#     "industrial IoT", "big data analytics", "cybersecurity in oil & gas",
#     "SCADA", "remote monitoring", "5G in oil & gas", "AI-driven optimization",
#     "process automation", "digital oilfield", "smart sensors", "machine vision",

#     # AI & Machine Learning Applications
#     "AI-assisted drilling", "AI in reservoir simulation", "reinforcement learning in drilling",
#     "predictive maintenance AI", "autonomous drilling", "AI-powered seismic interpretation",
#     "cognitive computing in exploration", "deep learning for oilfield analytics",
#     "AI-based pipeline monitoring", "LLM", "LLMs in oil and gas",

#     # ... (you can include the rest as needed)
# ]

# # ==========================
# # 1. Text Extraction
# # ==========================
# def extract_text(input_path):
#     """
#     Extracts text from a PDF using pdfplumber if the file ends with '.pdf',
#     otherwise reads the file as plain text.
#     """
#     text = ""
#     if input_path.lower().endswith(".pdf"):
#         try:
#             with pdfplumber.open(input_path) as pdf:
#                 for page in pdf.pages:
#                     page_text = page.extract_text()
#                     if page_text:
#                         text += page_text + "\n"
#         except Exception as e:
#             print(f"Error extracting text from PDF: {e}")
#             sys.exit(1)
#     else:
#         try:
#             with open(input_path, "r", encoding="utf-8") as f:
#                 text = f.read()
#         except Exception as e:
#             print(f"Error reading text file: {e}")
#             sys.exit(1)
#     return text

# # ==========================
# # 2. Relevance Scoring (Keyword-based)
# # ==========================
# def compute_relevance_score(text, keywords):
#     text_lower = text.lower()
#     keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
#     similarity_score = len(set(text_lower.split()) & set(keywords)) / len(set(text_lower.split()))
#     return (keyword_matches * 2 + similarity_score * 10) / (len(keywords) + 1) * 100

# # ==========================
# # 3. Summarization using LLM
# # ==========================
# def summarize_with_llm(text):
#     prompt = f"""
# You are an advanced AI model specializing in analyzing and summarizing articles related to technology, innovation, and industry trends.
# Your task is to generate a concise and informative summary that captures the key points and insights from the provided text.
# Ensure that the summary highlights major advancements, industry impact, and relevance to emerging trends.

# Here is the full article text:
# {text}

# Please provide a concise overview of the key technologies, innovations, and any forecasts mentioned.
# Provide a well-structured summary focusing on:
# - Core technological innovations
# - Industry impact and relevance
# - Future implications and trends
# """
#     return client.text_generation(prompt, max_new_tokens=1024)

# # ==========================
# # 4. Novelty Score using LLM Knowledge
# # ==========================
# def compute_novelty_score_llm(summary_text):
#     """
#     Uses the LLM to evaluate how novel/innovative the primary technology in the summary is.
#     The prompt instructs the model to provide a numerical score between 0 and 100.
#     """
#     prompt = f"""
# You are an expert in technological trends and innovation.
# Based on your extensive knowledge, please evaluate the following summary text and rate the novelty of the primary technology mentioned.
# Rate on a scale from 0 to 100 where:
# 0 means the technology is well-established and common,
# 100 means it is extremely novel and innovative.
# Provide only the numerical score.

# Summary:
# \"\"\"{summary_text}\"\"\"
# """
#     response = client.text_generation(prompt, max_new_tokens=16)
#     # Extract number from the response (assuming the model outputs a number)
#     try:
#         # Use regex to extract a number (it might output "85" or "85/100", etc.)
#         num_match = re.search(r'(\d+)', response)
#         if num_match:
#             return int(num_match.group(1))
#     except Exception as e:
#         print(f"Error parsing novelty score: {e}")
#     return 0  # Fallback score

# # ==========================
# # 5. Extract Primary Technology from Text
# # ==========================
# def extract_primary_technology(text):
#     """
#     Identify the primary technology mentioned in the text by counting frequency of known technology keywords.
#     Returns the keyword with the highest occurrence count or None if none are found.
#     """
#     text_lower = text.lower()
#     tech_counts = {}
#     for kw in TECHNOLOGY_KEYWORDS:
#         count = text_lower.count(kw.lower())
#         if count > 0:
#             tech_counts[kw] = count
#     if tech_counts:
#         # Return the keyword with the highest frequency
#         return max(tech_counts, key=tech_counts.get)
#     return None

# # ==========================
# # 6. Heat Score by Comparing with Other Articles in the Database
# # ==========================
# def compute_heat_score_db(summary_text):
#     """
#     Computes a heat score based on how many articles in the database mention the primary technology.
#     For example, if many articles discuss the same technology, it indicates high trending interest.
#     The score is scaled to a maximum of 100.
#     """
#     primary_tech = extract_primary_technology(summary_text)
#     if not primary_tech:
#         return 0

#     try:
#         conn = sqlite3.connect(DATABASE)
#         c = conn.cursor()
#         # Search in both full_text and snippet for the primary technology.
#         query = "SELECT COUNT(*) FROM articles WHERE full_text LIKE ? OR snippet LIKE ?"
#         like_pattern = f"%{primary_tech}%"
#         c.execute(query, (like_pattern, like_pattern))
#         count = c.fetchone()[0]
#         conn.close()
#         # Scale: for example, each article adds 10 points up to a maximum of 100.
#         score = min(100, count * 10)
#         return score
#     except Exception as e:
#         print(f"Error computing heat score: {e}")
#         return 0

# # ==========================
# # Main Execution
# # ==========================
# if __name__ == "__main__":
#     if len(sys.argv) > 1:
#         input_path = sys.argv[1]
#     else:
#         print("Usage: python LLM_Summary.py <input_file>")
#         sys.exit(1)
    
#     input_text = extract_text(input_path)
#     if not input_text.strip():
#         print("No text found in the input file. Exiting.")
#         sys.exit(1)
    
#     # Generate summary using the LLM
#     summary = summarize_with_llm(input_text)
    
#     # Compute scores
#     relevance_score = compute_relevance_score(input_text, ["AI", "machine learning", "energy", "ESG", "sustainability", "oil", "gas"])
#     novelty_score = compute_novelty_score_llm(summary)
#     heat_score = compute_heat_score_db(summary)
    
#     # Print outputs in a format that can be parsed by the fetching script
#     print("SUMMARY:", summary)
#     print("RELEVANCE SCORE:", relevance_score)
#     print("NOVELTY SCORE:", novelty_score)
#     print("HEAT SCORE:", heat_score)
