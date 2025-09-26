import os
import json
import pandas as pd
import sqlite3
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser # <<< CHANGED: Import the JSON parser

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

# <<< CHANGED: Define the parser and chain correctly
parser = JsonOutputParser()
chain = prompt | llm | parser

# ------------------------------
# Connect to SQLite database
# ------------------------------
# Make sure the path is correct relative to where you run the script
conn = sqlite3.connect("Prototype/argo_data.db")

# ------------------------------
# Flask App
# ------------------------------
app = Flask(__name__)

@app.route("/query", methods=["POST"]) # <<< CHANGED: POST is more appropriate for sending data
def query_argo():
    # <<< CHANGED: Get the query from the request body
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400
    user_query = data.get("query")

    try:
        # Run LLM chain - it now directly returns a dictionary
        response_dict = chain.invoke({"user_query": user_query}) # <<< CHANGED

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
        # Generic error handler for LLM or SQL issues
        return jsonify({"error": str(e)}), 500

# ------------------------------
# Run Flask
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)