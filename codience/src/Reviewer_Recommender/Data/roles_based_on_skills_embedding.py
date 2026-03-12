import os
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "rag_ready_data.csv")


db_dir = os.path.join(current_dir, "my_vector_db")

loader = CSVLoader(file_path=csv_path)
docs = loader.load()

# Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 3. Build & Save Database
# Adding 'persist_directory' automatically saves it to your drive
vectorstore = Chroma.from_documents(
    documents=docs, 
    embedding=embeddings, 
    persist_directory=db_dir
)

print(f"Success! Database saved to: {db_dir}")