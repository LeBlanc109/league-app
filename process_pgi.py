import pandas as pd

def parse_match_results(results_json):
    """Extracts static context (champ, win, identity) to merge with timeline."""
    match_id = results_json['metadata']['matchId']
    participants = []

    for p in results_json['info']['participants']:
        row = {
            'match_id': match_id,
            'participant_id': p['participantId'],
            'champion_name': p['championName'],
            'win': int(p['win']),
            'summoner_name': p.get('riotIdGameName', ''),
            'summoner_tag': p.get('riotIdTagline', ''),
            'team_position': p.get('teamPosition', ''),
            'summoner_spell_1': p.get('summoner1Id'),
            'summoner_spell_2': p.get('summoner2Id'),
            'ended_in_surrender': int(p.get('gameEndedInSurrender', False)),
            'ended_in_early_surrender': int(p.get('gameEndedInEarlySurrender', False)),
        }
        participants.append(row)
    pgi = pd.DataFrame(participants)
    return pgi