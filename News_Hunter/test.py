import requests

headers = {
    "Authorization": "Bearer 162b7ccbd22146709dc6bdd640cf65af95248d1a49df419659c4444b780be563",
    "Content-Type": "application/json"
}
data = {
    "zone": "varun1", # Confirm kar lena yehi zone hai.
    # 👇 Yahan change karna hai: '^&' ko sirf '&' kar do
    "url": "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api",
    "format": "raw"
}

response = requests.post(
    "https://api.brightdata.com/request",
    json=data,
    headers=headers
)
print(response.text)