import requests

url = "http://127.0.0.1:5000/query"
payload = {
    "query": "Show me temperature and salinity for 2003-01-10"
}

response = requests.post(url, json=payload)
print(response.json())
