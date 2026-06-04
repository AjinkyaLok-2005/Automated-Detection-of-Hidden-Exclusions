import pandas as pd

train_df = pd.read_csv('data/processed/train.csv')
test_df  = pd.read_csv('data/processed/test.csv')

# Check if source_document column exists
print(train_df.columns.tolist())

# If there's a document/file/source column:
train_docs = set(train_df['source_file'].unique())
test_docs  = set(test_df['source_file'].unique())

overlap = train_docs.intersection(test_docs)
print(f"Overlapping documents: {len(overlap)}")
print(f"Train docs: {len(train_docs)}")
print(f"Test docs : {len(test_docs)}")