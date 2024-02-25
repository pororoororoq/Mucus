from dotenv import load_dotenv
import os
import base64
import json
from requests import post, get
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

def get_auth_header(token):
        return {"Authorization": "Bearer " + token}

class Spotify(object):    
    def get_token():
        auth_string = client_id + ':' + client_secret
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": "Basic " + auth_base64,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {"grant_type": "client_credentials"}
        result = post(url, headers=headers, data=data)
        json_result = json.loads(result.content)
        token = json_result["access_token"]
        return token

    def search_for_track(token, track_name):
        url = "https://api.spotify.com/v1/search"
        headers = get_auth_header(token)
        query = f"?q={track_name}&type=track&limit=5"

        query_url = url + query
        result = get(query_url, headers=headers)
        json_result = json.loads(result.content)
        if len(json_result) == 0:
            print("No results")
            return None
    
        return json_result
    

    def get_songs_by_artist(token, artist_id):
        url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US"
        headers = get_auth_header(token)
        result = get(url, headers=headers)
        json_result = json.loads(result.content)["tracks"]
        return json_result

    def get_audio_analysis(token, song_id):
        url = f"https://api.spotify.com/v1/audio-analysis/{song_id}"
        headers = get_auth_header(token)
        result = get(url, headers=headers)
        json_result = json.loads(result.content)
        return json_result

    def get_audio_features(token, song_id):
        url = f"https://api.spotify.com/v1/audio-features/{song_id}"
        headers = get_auth_header(token)
        result = get(url, headers=headers)
        json_result = json.loads(result.content)
        return json_result  
        
    

    token = get_token()
    track_name = input("Track Title: ")
    track_data = search_for_track(token, track_name)["tracks"]

    for i in range(5):
        print_data = []
        artist_names = []
        for track in track_data["items"][i]["artists"]:
            artist_names += [track['name']]
        print_data.append(artist_names)
        print_data.append(track_data["items"][i]["name"])
        print(i+1, print_data)

    index = int(input("Which one? (Type in a number): "))
    track_id = track_data["items"][index-1]["id"]

    analysis = get_audio_features(token, track_id)
    print(analysis)


class Song(object):
    def __init__(self, length, category):
        self.length = length
        self.category = category

    