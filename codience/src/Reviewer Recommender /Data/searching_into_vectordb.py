import os
import warnings
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Clean up the output console
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)

# 1. Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(current_dir, "my_vector_db")

# 2. Setup the "Brain"
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 3. Load the existing database
print("--- Checking Vector Database ---")
vectorstore = Chroma(persist_directory=db_dir, embedding_function=embeddings)

# 4. VERIFY: Count the items
# Accessing the internal collection to see how many rows were indexed
item_count = vectorstore._collection.count()
print(f"Status: Database Loaded Successfully.")
print(f"Items Found: {item_count} documents are in the database.")

if item_count == 0:
    print("Warning: The database is empty. You might need to re-run your 'Save' script.")
else:
    # 5. SEARCH: Test a query
    print("\n--- Running Test Search ---")
    query = "Who has experience with Python and data visualization?"
    
    # k=2 returns the top 2 matches
    results = vectorstore.similarity_search(query, k=4)

    for i, res in enumerate(results):
        print(f"\nResult #{i+1}:")
        print(res.page_content)