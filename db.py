import pandas as pd
from pymongo import MongoClient

# Read the CSV file
df = pd.read_csv('mod_knn.csv')

# Connect to the MongoDB server
client = MongoClient('mongodb://localhost:27017/')

# Create a database
db = client['mydatabase']

# Create a collection
collection = db['mycollection']

# Convert DataFrame to list of dictionaries
data = df.to_dict(orient='records')

# Insert data into MongoDB
collection.insert_many(data)

print("Data inserted successfully!")