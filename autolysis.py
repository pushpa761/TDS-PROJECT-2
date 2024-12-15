# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "seaborn",
#   "pandas",
#   "matplotlib",
#   "httpx",
#   "chardet",
#   "numpy",
#   "requests",
#   "openai",
#   "scipy",
#   "scikit-learn",
#   "python-dotenv",
#   "ipykernel",
#   "python-dotenv",
# ]
# ///
import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import chardet
import requests
import openai
import traceback
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from dotenv import load_dotenv  # For loading environment variables from .env file
from scipy.stats import zscore



# Step 3: Read API Token from Environment Variable
api_proxy_token = os.environ["AIPROXY_TOKEN"]
if not api_proxy_token:
    raise ValueError("API proxy token not found. Please set the 'AIPROXY_TOKEN' in the .env file.")


# Function to detect the encoding of a file
def detect_encoding(filename):
    """Detect file encoding."""
    with open(filename, 'rb') as file:
        result = chardet.detect(file.read(1024))  # Read the first 1 KB for detection
        return result['encoding']


# Function to read a CSV file
def read_csv(filename):
    """Read the dataset with the correct encoding."""
    encodings_to_try = [detect_encoding(filename), 'utf-8', 'utf-8-sig', 'latin1', 'ISO-8859-1']
    for encoding in encodings_to_try:
        try:
            df = pd.read_csv(filename, encoding=encoding)
            print(f"Dataset loaded: {filename} (Encoding: {encoding})")
            return df
        except Exception as e:
            print(f"Failed with encoding {encoding}: {e}")
    print(f"All encoding attempts failed for {filename}.")
    return None


# Function to analyze the dataset
def analyze_data(df):
    """Analyze the dataset and return a summary."""
    try:
        analysis = {
            "dataset": df.head().to_dict(),
            "shape": df.shape,
            "columns": df.dtypes.to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "summary_statistics": df.describe(include="all").to_dict(),
        }

        def outlier_detection(df):
            numeric_df = df.select_dtypes(include=[np.number])
            z_scores = numeric_df.apply(zscore)
            numeric_data = df.select_dtypes(include=["number"])
            return numeric_data, (np.abs(z_scores) > 3).sum()

        numeric_data, outliers = outlier_detection(df)
        analysis["outliers"] = outliers.to_dict()

        if not numeric_data.empty:
            analysis["correlation_matrix"] = numeric_data.corr().to_dict()
        else:
            analysis["correlation_matrix"] = None

        return analysis
    except Exception as e:
        print(f"Error analyzing data: {e}")
        traceback.print_exc()
        return {}


# Function to visualize the dataset
def visualize_data(df, output_prefix):
    """Generate visualizations for the dataset."""
    charts = []
    try:
        # Select numeric columns
        numeric_columns = df.select_dtypes(include=["number"])
        if numeric_columns.empty:
            print("No numeric columns found in the dataset.")
            return charts

        # Ensure column names are strings
        numeric_columns.columns = numeric_columns.columns.astype(str)

        # Distribution of numeric columns
        for column in numeric_columns.columns:
            plt.figure(figsize=(8, 5))
            numeric_columns[column].hist(bins=30, color="skyblue", edgecolor="black")
            plt.title(f"Distribution of {column}")
            plt.xlabel(column)
            plt.ylabel("Frequency")
            dist_file = f"{output_prefix}_{column}_distribution.png"
            plt.savefig(dist_file, dpi=300)
            charts.append(dist_file)
            plt.close()

        # Correlation Heatmap
        plt.figure(figsize=(14, 12))
        heatmap = sns.heatmap(
            numeric_columns.corr(),
            annot=True,
            cmap="coolwarm",
            fmt=".2f",
            cbar_kws={'shrink': 0.8}
        )
        heatmap.set_title("Correlation Heatmap")
        heatmap_file = f"{output_prefix}_heatmap.png"
        plt.savefig(heatmap_file, dpi=300)
        charts.append(heatmap_file)
        plt.close()

      
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_columns)

        # Impute missing values in scaled data
        imputer = SimpleImputer(strategy='mean')
        scaled_data_imputed = imputer.fit_transform(scaled_data)

        # K-Means Clustering
        inertia = []
        silhouette_scores = []
        max_clusters = min(10, len(df))  # Limit clusters for small datasets
        for k in range(2, max_clusters + 1):
            kmeans = KMeans(n_clusters=k, random_state=42)
            cluster_labels = kmeans.fit_predict(scaled_data_imputed)
            inertia.append(kmeans.inertia_)
            silhouette_scores.append(silhouette_score(scaled_data_imputed, cluster_labels))

        # Elbow Method Plot
        plt.figure(figsize=(8, 6))
        plt.plot(range(2, max_clusters + 1), inertia, marker='o', linestyle='--')
        plt.xlabel("Number of Clusters")
        plt.ylabel("Inertia")
        plt.title("Elbow Method for Optimal Clusters")
        elbow_file = f"{output_prefix}_elbow_method.png"
        plt.savefig(elbow_file, dpi=300)
        charts.append(elbow_file)
        plt.close()

        # Silhouette Score Plot
        plt.figure(figsize=(8, 6))
        plt.plot(range(2, max_clusters + 1), silhouette_scores, marker='o', linestyle='--')
        plt.xlabel("Number of Clusters")
        plt.ylabel("Silhouette Score")
        plt.title("Silhouette Score for Optimal Clusters")
        silhouette_file = f"{output_prefix}_silhouette_score.png"
        plt.savefig(silhouette_file, dpi=300)
        charts.append(silhouette_file)
        plt.close()

        # Choose optimal clusters based on silhouette score
        optimal_clusters = silhouette_scores.index(max(silhouette_scores)) + 2

        # Hierarchical Clustering
        linked = linkage(scaled_data_imputed, method='ward')
        plt.figure(figsize=(12, 8))
        dendrogram(linked, orientation='top', distance_sort='descending', show_leaf_counts=False)
        plt.title("Hierarchical Clustering Dendrogram")
        dendrogram_file = f"{output_prefix}_dendrogram.png"
        plt.savefig(dendrogram_file, dpi=300)
        charts.append(dendrogram_file)
        plt.close()

    except Exception as e:
        print(f"Error generating visualizations: {e}")
        traceback.print_exc()

    return charts


# Function to interact with the LLM (via API Proxy)
def interact_with_llm_optimized(filename, analysis, api_token):
    """Interact with the gpt-4o-mini LLM via the API Proxy with reduced tokens."""
    import json  # Ensure payload and response debugging

    try:
        # API Proxy Base URL and Endpoint
        api_proxy_base_url = "https://aiproxy.sanand.workers.dev"
        api_url = f"{api_proxy_base_url}/openai/v1/chat/completions"

        # Request Headers
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        # Construct Optimized Prompt
        prompt = (
            f"The dataset named '{filename}' with:\n"
            f"- Structure: {analysis.get('dataset')}\n"
            f"- Shape: {analysis.get('shape')}\n"
            f"- Columns: {list(analysis.get('columns').keys())}\n"
            f"- Correlation Matrix: {analysis.get('correlation_matrix')}\n"
            f"- Outliers: {analysis.get('outliers')}\n"
            f"- Missing Values Count: {sum(analysis.get('missing_values').values())}\n\n"
            " Discuss key insights such as outlier impacts, correlations, and clustering patterns and provide useful  suggestions for furthur improvements along with data summary."
        )

        # Request Payload with reduced tokens
        payload = {
            "model": "gpt-4o-mini",  # The required model
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,  # Reduced token limit
            "temperature": 0.5,  # Lower temperature for focused responses
            "top_p": 0.9  # Slightly narrower randomness for efficiency
        }

        # Send API Request
        response = requests.post(api_url, headers=headers, json=payload)

        # Handle Response
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            raise ValueError(f"API Request failed with status code {response.status_code}: {response.text}")

    except Exception as e:
        print(f"Error interacting with LLM: {e}")
        traceback.print_exc()
        return "Failed to generate insights from the LLM."


# Function to save the analysis and insights to a Markdown file
def save_markdown(analysis, charts, insights, output_file):
    """Save analysis, insights, and visualizations to a Markdown file."""
    try:
        with open(output_file, "w") as f:
            f.write("# Analysis Report\n\n")
            f.write("## Dataset Analysis\n")
            f.write(f"Structure: {analysis.get('dataset')}\n")
            f.write(f"Shape: {analysis.get('shape')}\n")
            f.write(f"Columns:\n{analysis.get('columns')}\n")
            f.write(f"Missing Values:\n{analysis.get('missing_values')}\n")
            f.write(f"Summary Statistics:\n{analysis.get('summary_statistics')}\n")
            f.write("\n## LLM Insights\n")
            f.write(insights + "\n")
            f.write("\n## Charts\n")
            for chart in charts:
                f.write(f"![{chart}]({chart})\n")
    except Exception as e:
        print(f"Error saving Markdown file: {e}")
        traceback.print_exc()


# Main function to process the CSV file
def main_optimized(filename):
    """Main function to process the dataset and generate insights with minimal cost."""
    print(f"Processing {filename}...")
    df = read_csv(filename)
    if df is None:
        return

    # Impute missing values in numeric columns
    imputer = SimpleImputer(strategy='mean')
    df_imputed = pd.DataFrame(imputer.fit_transform(df.select_dtypes(include=["number"])))
    df[df_imputed.columns] = df_imputed

    analysis = analyze_data(df)
    output_prefix = os.path.splitext(os.path.basename(filename))[0]
    charts = visualize_data(df, output_prefix)

    # Only request insights if dataset is small/important
    if len(df) <= 10000:  # Example threshold
        insights = interact_with_llm_optimized(filename, analysis, api_proxy_token)
    else:
        insights = "Dataset too large for insights within token budget."

    readme_file = f"{output_prefix}_README.md"
    save_markdown(analysis, charts, insights, readme_file)
    print(f"Completed analysis for {filename}. Results saved to {readme_file}.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: uv run autolysis.py <dataset_path>")
        sys.exit(1)
    filename= sys.argv[1]   
    main_optimized(filename)
