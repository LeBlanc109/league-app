import requests
from riot_auth import api_key

#gameName = 'AirBourneTiger'
#tagLine = 'FISH'
#rg_key = api_key


def get_puuid(gameName, tagLine, rg_key):
    puuid_endpoint = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}?api_key={rg_key}'
    puuid_response_in_json = requests.get(puuid_endpoint).json()
    puuid_string = puuid_response_in_json["puuid"]
    return puuid_string

def get_match_list_ids(puuid_string , rg_key):
    matchlist_ids_endpoint = f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid_string}/ids?start=0&count=3&api_key={rg_key}'
    matchlist_response_in_json = requests.get(matchlist_ids_endpoint).json()
    #only doing 3 to test
    return matchlist_response_in_json

def get_last_match_timeline(requested_matchId , rg_key):
    match_timeline_endpoint = f'https://americas.api.riotgames.com/lol/match/v5/matches/{requested_matchId}/timeline?api_key={rg_key}'
    timeline_in_json = requests.get(match_timeline_endpoint).json()
    return timeline_in_json

def get_pgi(requested_pgi , rg_key):
    pgi_endpoint = f'https://americas.api.riotgames.com/lol/match/v5/matches/{requested_pgi}?api_key={rg_key}'
    pgi_in_json = requests.get(pgi_endpoint).json()
    return pgi_in_json

def get_emerald_players(rg_key):
    emerald_endpoint = f'https://na1.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/EMERALD/I?page=1&api_key={rg_key}'
    emerald_in_json = requests.get(emerald_endpoint).json()
    emerald_list = [item["puuid"] for item in emerald_in_json]
    return emerald_list


