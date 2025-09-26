import requests

url = "https://sih-hackethon-prototype.onrender.com/"
payload = {
    "query": "Show me temperature and salinity for 2003-01-10"
}

response = requests.post(url, json=payload)
print(response.json())
