import os
import warnings
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

warnings.filterwarnings("ignore", category=UserWarning, module="chromadb")
warnings.filterwarnings("ignore", category=DeprecationWarning)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(CURRENT_DIR, "commit_vector_db_minilm")

# Use MiniLM's modern, lightweight embedding model for faster semantic search
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

def get_commit_vector_db():
    return Chroma(persist_directory=DB_DIR, embedding_function=embeddings)

def index_commits_to_db(commits_data: list):
    """
    Expects a list of dicts: 
    [{"author": "username", "sha": "commit_sha", "filename": "file.py", "patch": "diff code..."}]
    """
    if not commits_data:
        return
        
    db = get_commit_vector_db()
    
    # Split large diffs into sensible chunks so the vector search is accurate
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    
    texts = []
    metadatas = []
    
    for item in commits_data:
        if not item.get("patch"):
            continue
            
        chunks = text_splitter.split_text(item["patch"])
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({
                "author": item.get("author", "unknown"),
                "sha": item.get("sha", "unknown"),
                "filename": item.get("filename", "unknown")
            })
            
    if texts:
        db.add_texts(texts=texts, metadatas=metadatas)

def search_similar_commits(pr_patch: str, k=20):
    if not pr_patch:
        return []
        
    db = get_commit_vector_db()
    results = db.similarity_search(pr_patch, k=k)
    return results
