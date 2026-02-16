import pickle
import pandas as pd
from shapely.wkt import dumps

file_path = 'ResPlan.pkl'

try:
    with open(file_path, 'rb') as f:
        data = pickle.load(f)

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(data)

    # The geometric objects cannot be saved to CSV directly.
    # We must convert them to string format (WKT) first.
    # We apply this to every cell in the dataframe.
    df_str = df.applymap(lambda x: x.wkt if hasattr(x, 'wkt') else str(x))

    # Save to CSV
    output_filename = 'ResPlan_extracted.csv'
    df_str.to_csv(output_filename, index=False)
    
    print(f"Success! Extracted {len(df)} floor plans to '{output_filename}'")

except Exception as e:
    print(f"Error: {e}")