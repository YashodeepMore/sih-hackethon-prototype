import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
import re
from flask import Flask, request, jsonify


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

Return the output in JSON format:

{
"Generated_SQL": "<SQL query here>",
"Explanation": "<plain-text explanation here>"
}

User Query: {user_query}
"""

prompt = PromptTemplate(input_variables=["user_query"], template=template_str)
chain = LLMChain(prompt=prompt, llm=llm)

# ------------------------------
# Connect to SQLite database (already stored)
# ------------------------------
# Assume you have already created 'argo_data.db' and populated 'argo_data' table
conn = sqlite3.connect("Prototype/argo_data.db")  # persistent DB

# ------------------------------
# Flask App
# ------------------------------
app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query_argo():
    data = request.get_json()
    user_query = data.get("query", "")

    # Run LLM chain
    response = chain.invoke({"user_query": user_query})
    response_text = response.content if hasattr(response, "content") else str(response)
    response_dict = json.loads(response_text)
    
    sql_query = response_dict["Generated_SQL"].strip()
    explanation = response_dict["Explanation"].strip()

    # Execute SQL
    try:
        result_df = pd.read_sql(sql_query, conn)
    except Exception as e:
        return jsonify({"error": str(e), "sql_query": sql_query}), 400

    # Prepare JSON response
    response_json = {
        "data": result_df.to_dict(orient="records"),
        "explanation": explanation,
        "generated_sql": sql_query
    }

    return jsonify(response_json)

# ------------------------------
# Run Flask
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
