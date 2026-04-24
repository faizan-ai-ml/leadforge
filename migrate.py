import os
import glob
import re

files = glob.glob('frontend/**/*.tsx', recursive=True)
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace 'http://127.0.0.1:8000/api/...' -> `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/...`
    new_content = re.sub(
        r"'http://(?:127\.0\.0\.1|localhost):8000(.*?)'",
        r"`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}\1`",
        content
    )
    
    # Replace `http://127.0.0.1:8000/api/${id}` -> `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/${id}`
    new_content = re.sub(
        r"`http://(?:127\.0\.0\.1|localhost):8000(.*?)`",
        r"`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}\1`",
        new_content
    )
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)
print("Migration completed.")
