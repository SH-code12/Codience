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
    
    # 
    results = vectorstore.similarity_search(query, k=4)

    for i, res in enumerate(results):
        print(f"\nResult #{i+1}:")
        print(res.page_content)


# 6. NEW: Deduplication Logic
query = "Python and Data Science"
results = vectorstore.similarity_search(query, k=10) # Ask for 10 to find enough unique ones

unique_roles = []
seen_roles = set() 

for res in results:
    # Extract the Role name from the page_content string
    # (Assuming your text starts with "Role: RoleName | ...")
    role_name = res.page_content.split('|')[0].replace("rag_content: Role:", "").strip()
    
    if role_name not in seen_roles:
        unique_roles.append(res)
        seen_roles.add(role_name)
    
    # Stop once we have 3 unique recommendations
    if len(unique_roles) == 3:
        break

print("\n--- Top 3 Unique Recommendations ---")
for i, res in enumerate(unique_roles):
    print(f"\nRecommendation #{i+1}:")
    print(res.page_content)