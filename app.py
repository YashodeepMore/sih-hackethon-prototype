import os
import sqlite3
import pandas as pd
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# --- Initialization ---
load_dotenv()

# Initialize LLM
llm = ChatOpenAI(
    model="deepseek/deepseek-chat-v3.1:free",
    openai_api_base="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0
)

# --- LangChain Setup ---
template_str = """
You are an AI assistant for ARGO float data. The database table is `argo_data` with columns:
uid (INT), platform_number (INT), cycle_number (INT), latitude (FLOAT),
longitude (FLOAT), pressure (FLOAT), temperature (FLOAT), salinity (FLOAT), juld (FLOAT).

Note: The 'juld' column represents days since 1950-01-01 (Julian Day).
- If the user asks for a specific date, convert it to juld and select all rows for that date.
- If no date is mentioned, do not filter by juld.

Instructions:
1. Generate a SQL query that retrieves the requested data.
2. Generate a simple, human-readable explanation of the query result in no more than 100 words.

Return the output in JSON format only, with no other text before or after the JSON object.

{{
"Generated_SQL": "<SQL query here>",
"Explanation": "<plain-text explanation here>"
}}

User Query: {user_query}
"""

prompt = PromptTemplate(template=template_str, input_variables=["user_query"])
parser = JsonOutputParser()
chain = prompt | llm | parser

# --- Database Connection (Handles both Render and Local) ---
DB_FILE = "argo_data.db"
DB_PATH = DB_FILE

# On Render, the persistent disk is mounted at /var/data
# We check for the 'RENDER' environment variable to determine the path
if os.getenv("RENDER"):
    DATA_DIR = "/var/data"
    DB_PATH = os.path.join(DATA_DIR, DB_FILE)
    # Ensure the directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

# check_same_thread=False is required for Flask to share the connection across requests
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

# --- Flask Application ---
app = Flask(__name__)

@app.route("/query", methods=["GET","POST"])
def query_argo():
    """API endpoint to process a natural language query."""
    data = request.get_json()
    # if not data or "query" not in data:
    #     return jsonify({"error": "Missing 'query' in request body"}), 400
    
    # user_query = data.get("query")
    user_query= "Show me temperature and salinity for cycle 224"

    try:
        # Run the LangChain chain to get SQL and explanation
        response_dict = chain.invoke({"user_query": user_query})
        
        sql_query = response_dict.get("Generated_SQL", "").strip()
        explanation = response_dict.get("Explanation", "").strip()

        if not sql_query:
            return jsonify({"error": "Failed to generate SQL query from the model."}), 500

        # Execute the generated SQL query
        result_df = pd.read_sql(sql_query, conn)

        # Prepare the final JSON response
        response_json = {
            "data": result_df.to_dict(orient="records"),
            "explanation": explanation,
            "generated_sql": sql_query
        }
        return jsonify(response_json)

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred."}), 500

# This block is for local testing and will not be used by Gunicorn on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

