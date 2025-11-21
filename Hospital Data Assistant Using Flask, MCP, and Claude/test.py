import requests

# Your Marketstack API key
API_KEY = 'de4d7593fb5a1b9e564094e8e75bb8b9'

# Specify endpoint and parameters
url = 'http://api.marketstack.com/v1/eod'
params = {
    'access_key': API_KEY,
    'symbols': 'AAPL'  # Example: Apple Inc.
}

# Make the GET request
response = requests.get(url, params=params)

# Check response status and print data
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print('Error:', response.status_code)