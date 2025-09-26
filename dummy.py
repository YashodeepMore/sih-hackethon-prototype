import requests

url = "http://127.0.0.1:5000/query"
payload = {"query": "Show me temperature and salinity for cycle 224"}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
