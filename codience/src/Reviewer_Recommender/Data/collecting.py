public_repos=[

]



def get_publicPrs():
    # need to be completed
    for url in public_repos:
        print(url)



# clean the pull requests to be feeded to LLM
def clean_diff(raw_diff):
    # Split diff into file hunks
    files = raw_diff.split('diff --git')
    cleaned_hunks = []
    
    # Ignore binary files, lockfiles, and documentation
    ignore_list = ['.json', '.lock', '.md', '.txt', 'vendor/']
    
    for file_diff in files:
        if any(ext in file_diff.split('\n')[0] for ext in ignore_list):
            continue
        cleaned_hunks.append(file_diff)
        
    # Limit total size to avoid context overflow (approx 10k tokens)
    return "\n".join(cleaned_hunks)[:30000]

        
