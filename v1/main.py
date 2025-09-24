import os

# Create directories if they do not exist
directories = ['output', 'backup', 'logs']
for dir in directories:
    os.makedirs(dir, exist_ok=True)