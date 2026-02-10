import time
import pandas as pd
from riot_auth import api_key
from brain import activate_brain
import annoying as brain_neuron
import logging

logging.basicConfig(level=logging.INFO)

#import PATH??

## RIOT Rate Limits
## Every 2 Minutes : 100 Requests Cap
## (Also, 20, every second...)

class RateLimiter:
    def __init__(self):
        self.total_calls = 0

    def wait(self):
        self.total_calls += 1
        print(f"Progress: {self.total_calls} / XXX calls")
        if self.total_calls % 50 == 0:
            print(f"Progress: {self.total_calls} / ~1401 calls")
        time.sleep(1.2)
           
limiter = RateLimiter()

def feed():
    rg_key = api_key
    
    print("Starting Pipeline...")
    all_results = []
    
    #Populate List of PUUIDS
    limiter.wait()
    emerald_player_list = brain_neuron.get_emerald_players(rg_key)
    
    #now get the last 3 matches
    for player in emerald_player_list:
        limiter.wait()
        matches = brain_neuron.get_match_list_ids(player , api_key) #returns 3...

        for match_id in matches:
            limiter.wait()
            timeline = brain_neuron.get_last_match_timeline(match_id , rg_key)

            limiter.wait()
            post_gameinfo = brain_neuron.get_pgi(match_id, rg_key)

            json_to_df = activate_brain(timeline , post_gameinfo)
            all_results.append(json_to_df)

    # after the loops
    full_dataset = pd.concat(all_results, ignore_index=True)
    full_dataset.to_parquet("output.parquet", index=False)

if __name__ == "__main__":
    feed()





