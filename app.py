import os
import json
import pandas as pd
import sqlite3
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# ------------------------------
# Load environment
# ------------------------------
load_dotenv()

# ------------------------------
# Initialize LLM
# ------------------------------
llm = ChatOpenAI(
    model="deepseek/deepseek-chat-v3.1:free",
    openai_api_base="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0  # deterministic SQL generation
)

# ------------------------------
# Prompt template
# ------------------------------
template_str = """
You are an AI assistant for ARGO float data. The database table is `argo_data` with columns:
uid (INT), platform_number (INT), cycle_number (INT), latitude (FLOAT),
longitude (FLOAT), pressure (FLOAT), temperature (FLOAT), salinity (FLOAT), juld (FLOAT).

Note: The 'juld' column represents days since 1950-01-01 (Julian Day).
- If the user asks for a specific date, convert it to juld and select all rows for that date (include fractional days).
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

prompt = PromptTemplate(input_variables=["user_query"], template=template_str)
parser = JsonOutputParser()
chain = prompt | llm | parser

# ------------------------------
# <<< FIX: Connect to database conditionally for Render vs. Local >>>
# ------------------------------
# Check if the app is running on the Render platform
if os.getenv("RENDER"):
    # On Render, use the persistent disk path
    DATA_DIR = "/var/data"
    DB_PATH = os.path.join(DATA_DIR, "argo_data.db")
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    # Locally, use the database file in the same directory as the app
    DB_PATH = "argo_data.db"

conn = sqlite3.connect(DB_PATH)

# ------------------------------
# Flask App
# ------------------------------
app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query_argo():
    # Get the query from the request body
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400
    user_query = data.get("query")

    try:
        # Run LLM chain
        response_dict = chain.invoke({"user_query": user_query})

        sql_query = response_dict["Generated_SQL"].strip()
        explanation = response_dict["Explanation"].strip()

        # Execute SQL
        result_df = pd.read_sql(sql_query, conn)

        # Prepare JSON response
        response_json = {
            "data": result_df.to_dict(orient="records"),
            "explanation": explanation,
            "generated_sql": sql_query
        }

        return jsonify(response_json)

    except Exception as e:
        # Log the full error to the console for easier debugging on Render
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal error occurred. Check the server logs."}), 500

# ------------------------------
# Run Flask (for local testing only)
# ------------------------------
if __name__ == "__main__":
    # This block does not run on Render (Gunicorn is used instead).
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

