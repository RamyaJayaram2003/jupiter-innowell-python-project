import pdfplumber
import pandas as pd
from pymongo import MongoClient
import numpy as np
from fpdf import FPDF
import os

# Function to clean text
def clean_text(text):
    return text.replace('–', '-')  # Replace en dash with hyphen

# Step 1: Extract Tables from PDF
pdf_path = "input.pdf"  # Path to your PDF file

# Initialize an empty list to hold the tables
tables = []

# Open the PDF file
with pdfplumber.open(pdf_path) as pdf:
    # Extract table from page 1 (index 0)
    table1 = pdf.pages[0].extract_table()
    if table1:
        df1 = pd.DataFrame(table1[1:], columns=table1[0])  # Convert to DataFrame
        tables.append(df1)

    # Extract table from page 2 (index 1)
    table2 = pdf.pages[1].extract_table()
    if table2:
        df2 = pd.DataFrame(table2[1:], columns=table2[0])  # Convert to DataFrame
        df2 = df2.loc[~df2.index.duplicated(keep='first')]  # Drop duplicate indices
        tables.append(df2)

    # Extract table from page 3 (index 2)
    table3 = pdf.pages[2].extract_table()
    if table3:
        df3 = pd.DataFrame(table3[1:], columns=table3[0])  # Convert to DataFrame
        df3 = df3.loc[~df3.index.duplicated(keep='first')]  # Drop duplicate indices
        tables.append(df3)

# Combine the second table from page 2 and the second table from page 3 vertically
if 'df2' in locals() and 'df3' in locals():
    combined_vertical = pd.concat([df2.reset_index(drop=True), df3.reset_index(drop=True)], axis=0, ignore_index=True)  # Concatenate vertically
    tables.append(combined_vertical)  # Add the combined table to the list

# Combine all tables horizontally
if len(tables) > 0:
    combined_df = pd.concat(tables, axis=1)  # Concatenate along columns
else:
    combined_df = pd.DataFrame()  # If no tables found

# Save the extracted DataFrame to a CSV file
combined_df.to_csv('extracted_table.csv', index=False)  # Save to CSV

# Step 2: Store CSV Data in MongoDB
# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['costume']  # Replace with your database name
collection = db['spec']  # Replace with your collection name

# Read the CSV file and insert into MongoDB
df = pd.read_csv('extracted_table.csv')
collection.insert_many(df.to_dict('records'))

# Step 3: Retrieve Data from MongoDB
data = list(collection.find())
df_retrieved = pd.DataFrame(data)

# Step 4: Add Per Rate and Total Columns
# Add per rate column (random values between 0 and 2)
df_retrieved['per_rate'] = np.random.uniform(0, 2, size=len(df_retrieved))

# Ensure 'Qty' column exists and calculate total
if 'Qty' in df_retrieved.columns:
    df_retrieved['Total'] = df_retrieved['Qty'].astype(float) * df_retrieved['per_rate']
else:
    print("Column 'Qty' not found in the DataFrame. Please check the column names.")
    df_retrieved['Total'] = np.nan  # Set total to NaN if qty is not found

# Round per_rate and total to 2 decimal places
df_retrieved['per_rate'] = df_retrieved['per_rate'].round(2)
df_retrieved['Total'] = df_retrieved['Total'].round(2)

# Step 5: Handle Missing Values
# Replace NaN with empty strings for display purposes
df_retrieved.fillna('', inplace=True)

# Step 6: Drop the 'id' column if it exists
if '_id' in df_retrieved.columns:
    df_retrieved.drop(columns=['_id'], inplace=True)

# Step 7: Limit to 8 rows and select specific columns
df_limited = df_retrieved[['Placement', 'Composition', 'Qty', 'per_rate', 'Total']].head(8)  # Get only the first 8 rows

total_cost = df_limited['Total'].astype(float).sum() 

# Step 8: Extract additional information from the PDF
image_path = "extracted_image.png"  # Path to save the extracted image
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]  # Assuming the image is on the first page
    text = page.extract_text()
    lines = text.split('\n')
    
    # Extract specific fields
    style = "Style: " + clean_text(next(line for line in lines if "Style:" in line).split(":")[1].strip())
    style_number = "Style Number: " + clean_text(next(line for line in lines if "Style number:" in line).split(":")[1].strip())
    brand = "Brand: " + clean_text(next(line for line in lines if "Brand:" in line).split(":")[1].strip())
    sizes = "Sizes: " + clean_text(next(line for line in lines if "Sizes:" in line).split(":")[1].strip())
    commodity = "Commodity: " + clean_text(next(line for line in lines if "Commodity:" in line).split(":")[1].strip())
    email = "E-mail: " + clean_text(next(line for line in lines if "E-mail:" in line).split(":")[1].strip())
    care_address = "Care Address: " + clean_text(next(line for line in lines if "Care Address:" in line).split(":")[1].strip())

    # Extract the image from the PDF
    images = page.images
    if images:
        image = images[0]  # Assuming the first image is the one we want
        x0, y0, x1, y1 = image['x0'], image['top'], image['x1'], image['bottom']
        img = page.within_bbox((x0, y0, x1, y1)).to_image()
        img.save(image_path)  # Save the image

# Convert Final DataFrame to PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Set font
pdf.set_font("Arial", size=9)

# Add the image to the top right corner
pdf.image(image_path, x=150, y=10, w=40)  # Adjust x, y, and w as needed

pdf.cell(200, 10, txt="Costing Sheet", ln=True, align='C')

# Add extracted information above the table
pdf.set_font("Arial", style='B', size=10)
pdf.cell(0, 10, txt=style, ln=True)
pdf.cell(0, 10, txt=style_number, ln=True)
pdf.cell(0, 10, txt=brand, ln=True)
pdf.cell(0, 10, txt=sizes, ln=True)
pdf.cell(0, 10, txt=commodity, ln=True)
pdf.cell(0, 10, txt=email, ln=True)
pdf.cell(0, 10, txt=care_address, ln=True)
pdf.cell(0, 10, txt="", ln=True)  # Add a blank line for spacing

# Display total cost
pdf.cell(0, 10, txt=f"Total Cost: ${total_cost:.2f}", ln=True, align='C')

# Add table headers
pdf.set_font("Arial", size=10)

# Define column widths
column_widths = {
    "Placement": 30,
    "Composition": 70,
    "Qty": 30,
    "per_rate": 30,
    "Total": 30
}

# Add table headers with defined widths
for column in df_limited.columns:
    pdf.cell(column_widths.get(column, 30), 10, column, border=1, align='C')  # Default width is 30
pdf.ln()

# Add table rows
for index, row in df_limited.iterrows():
    for column in df_limited.columns:
        pdf.cell(column_widths.get(column, 30), 10, str(row[column]), border=1, align='C')
    pdf.ln()

# Add a summary row for total cost
pdf.cell(column_widths['Placement'], 10, '', border=1, align='C')  # Empty cell for Placement
pdf.cell(column_widths['Composition'], 10, '', border=1, align='C')  # Empty cell for Composition
pdf.cell(column_widths['Qty'], 10, '', border=1, align='C')  # Empty cell for Qty
pdf.cell(column_widths['per_rate'], 10, 'Total', border=1, align='C')  # Empty cell for per_rate
pdf.cell(column_widths['Total'], 10, f"{total_cost:.2f}", border=1, align='C')  # Total cost
pdf.ln()

# Save the PDF
pdf.output("final_data.pdf")

# Clean up the temporary image file
if os.path.exists(image_path):
    os.remove(image_path)

print("Final data saved to 'final_data.pdf'.")
