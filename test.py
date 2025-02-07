import requests

url = "https://en144.tribalwars.net/game.php"

map_file = "/map/village.txt"
"/map/player.txt"
"/map/ally.txt"
"/map/conquer.txt"

# url get 
url_get = url + map_file

# get request
response = requests.get(url_get)

print(response.text)