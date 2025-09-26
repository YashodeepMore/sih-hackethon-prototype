import requests

url = "https://sih-hackethon-prototype.onrender.com/query"
payload = {
    "query": "Show me temperature and salinity for cycle 224"
}

response = requests.post(url, json=payload)
print(response.json())
