import json
from concurrent import futures

import gcp_commands
import server_score_calculator
from edge_server_listener import get_server_scores_from_servers

THRESHOLD = 12


def formula(value, price):
    return value / price


with open("utils/prices.json", 'r') as file:
    prices = json.load(file)

max_price = max(prices, key=prices.get)
min_price = min(prices, key=prices.get)

deployed_regions = gcp_commands.list_deployed_regions()

print("deployed regions:" + str(deployed_regions))

with futures.ThreadPoolExecutor() as executor:
    results = [executor.submit(gcp_commands.get_vm_ips, region) for region in deployed_regions]

ips = []

for future in futures.as_completed(results):
    result = future.result()
    if result:
        ips.append(result[0])

scores = get_server_scores_from_servers(ips, "scores_in_region",
                                        {key: 0 for key in server_score_calculator.get_server_coords().keys()})

adding = []
removing = []

for region, score in scores.items():
    if score * (1.1 - (prices[region] - prices[min_price]) / (prices[max_price] - prices[min_price]) * 2) > THRESHOLD:
        adding.append(score.keys())
    elif region in deployed_regions:
        removing.append(region)

deployed = [item for item in deployed_regions if item not in removing]

deployed.extend(adding)

if not deployed:
    adding.append(max(scores, key=lambda k: formula(scores[k], prices[k])))
    if max(scores, key=lambda k: formula(scores[k], prices[k])) in removing:
        removing.remove(max(scores, key=lambda k: formula(scores[k], prices[k])))
else:
    print("feds")

print("adding: " + str(adding))
print("removing: " + str(removing))

gcp_commands.orchestrate(adding, removing)
