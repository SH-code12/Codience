from datasets import load_dataset
import pandas as pd

ds = load_dataset("fazni/roles-based-on-skills")


data_folder = ds['train']


df = data_folder.to_pandas()

df['rag_content'] = "Role: " + df['Role'] + " | Details: " + df['text']

df[['rag_content']].to_csv("rag_ready_data.csv", index=False)