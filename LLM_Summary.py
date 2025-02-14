"""
adnoc_summarizer.py
 
A script that:
1) Extracts text from a PDF using pdfplumber
2) Splits text into manageable chunks
3) Creates embeddings of chunks using a SentenceTransformer model
4) Stores embeddings in a FAISS vector index
5) Retrieves the most relevant chunks for a user query
6) Summarizes those chunks with a local open-source LLM (Falcon-7B-Instruct)
"""
 
import os
import sys
from huggingface_hub import InferenceClient
 
API_KEY = "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"  # Get from https://huggingface.co/settings/tokens
model = "mistralai/Mistral-7B-Instruct-v0.3"
 
client = InferenceClient(model=model, token=API_KEY)
# ==============================
# 1. Install necessary libraries
# ==============================
# NOTE: It's recommended to install these packages in a virtual environment
# or conda environment before running the script. For example:
# pip install pdfplumber PyPDF2 sentence-transformers faiss-cpu transformers accelerate torch
 
# If you need 4-bit or 8-bit quantization, install bitsandbytes:
# pip install bitsandbytes
# and see the model loading code for adjustments.
if len(sys.argv) > 1:
    pdf_path = sys.argv[1]

try:
    import pdfplumber
except ImportError:
    print("Please install pdfplumber: pip install pdfplumber")
    sys.exit(1)
 
try:
    import faiss
except ImportError:
    print("Please install faiss-cpu: pip install faiss-cpu")
    sys.exit(1)
 
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install sentence-transformers: pip install sentence-transformers")
    sys.exit(1)
 
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
except ImportError:
    print("Please install transformers and torch: pip install transformers torch")
    sys.exit(1)
 
# ==========================
# 2. PDF text extraction
# ==========================
def extract_text_from_pdf(pdf_path):
    """
    Extracts text from each page of the PDF and concatenates into a single string.
    """
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
 
 
# ==========================
# 3. Text chunking function
# ==========================
def chunk_text(text, max_tokens=300):
    """
    Splits text into chunks of ~max_tokens words each.
    Adjust the size based on the LLM's context window.
    """
    words = text.split()
    chunks = []
    current_chunk = []
    current_count = 0
 
    for word in words:
        current_chunk.append(word)
        current_count += 1
        if current_count >= max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_count = 0
 
    # Add any leftover words as a final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))
 
    return chunks
 
 
# ================================================
# 4. Build embeddings and FAISS index
# ================================================
def build_faiss_index(chunks, embedding_model_name='sentence-transformers/all-MiniLM-L6-v2'):
    """
    Creates embeddings for each chunk using a SentenceTransformer model
    and builds a FAISS index for similarity search.
    """
    embedder = SentenceTransformer(embedding_model_name)
    chunk_embeddings = embedder.encode(chunks, convert_to_numpy=True)
 
    # Create FAISS index
    dimension = chunk_embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(chunk_embeddings)
 
    return index, chunk_embeddings, embedder
 
 
def retrieve_relevant_chunks(query, index, chunks, embeddings, embedder, top_k=5):
    """
    Given a user query, embed the query and retrieve the top_k most relevant chunks.
    """
    query_embedding = embedder.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    relevant_chunks = [chunks[i] for i in indices[0]]
    return relevant_chunks
 
 
 
def summarize_with_llm(chunks, model, device="cuda"):
    """
    Summarizes the provided chunks with an LLM prompt.
    The prompt instructs the model to focus on oil & gas tech/innovation.
    """
    # You can customize the prompt to better reflect ADNOC context
    prompt = (
        "You are an assistant that summarizes documents focusing on technology, "
        "innovation, and future forecasts relevant to oil and gas operations for ADNOC.\n\n"
        "Document sections:\n"
    )
    for i, chunk in enumerate(chunks):
        prompt += f"[Section {i+1}] {chunk}\n\n"
 
    prompt += (
        "Please provide a concise overview of the key technologies, innovations, "
        "and any forecasts mentioned, focusing on ADNOC's strategic needs."
    )
 
    # Generate
    summary = client.text_generation(prompt, max_new_tokens=1024)
 
    return summary
 
# --------------------------
# 6.1. Set the paths/queries
# --------------------------

user_query = "Summarize the main technology and innovation insights relevant to ADNOC."
top_k = 5  # Number of relevant chunks to retrieve
 
# --------------------------
# 6.2. Extract PDF text
# --------------------------
print("[INFO] Extracting text from PDF...")
pdf_text = extract_text_from_pdf(pdf_path)
if not pdf_text.strip():
    print("No text found in PDF or PDF is scanned (no OCR). Exiting.")
else:
    # --------------------------
    # 6.3. Chunk the text
    # --------------------------
    print("[INFO] Splitting text into chunks...")
    chunks = chunk_text(pdf_text, max_tokens=300)
    print(f"[INFO] Created {len(chunks)} text chunks.")
 
    # --------------------------
    # 6.4. Build FAISS index
    # --------------------------
    print("[INFO] Creating embeddings and building FAISS index...")
    index, chunk_embeddings, embedder = build_faiss_index(chunks)
 
    # --------------------------
    # 6.5. Retrieve relevant chunks
    # --------------------------
    print("[INFO] Retrieving relevant chunks for the query...")
    relevant_chunks = retrieve_relevant_chunks(user_query, index, chunks, chunk_embeddings, embedder, top_k=top_k)
    print(f"[INFO] Top {top_k} relevant chunks retrieved.")
 
    # --------------------------
    # 6.7. Summarize with LLM
    # --------------------------
    print("[INFO] Summarizing the retrieved text with the LLM...")
    summary_result = summarize_with_llm(relevant_chunks, model, device="cuda")
 
    # --------------------------
    # 6.8. Print the summary
    # --------------------------
    print("\n=== SUMMARY RESULT ===")
    print(summary_result)
    print("======================\n")