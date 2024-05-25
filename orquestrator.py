import json
from concurrent import futures

import gcp_commands
from edge_server_listener import get_server_scores_from_servers

THRESHOLD = 12


def get_deployed_regions():
    with open('utils/deployed_regions.json', 'r') as file:
        data = json.load(file)

    return data


deployed_regions = get_deployed_regions

with futures.ThreadPoolExecutor() as executor:
    results = [executor.submit(gcp_commands.get_vm_ips, region) for region in regions]

ips = []

for future in futures.as_completed(results):
    result = future.result()
    if result:
        ips.append(result[0])

scores = get_server_scores_from_servers(ips, "scores_in_region", {})

adding = []
removing = []

for score in scores:
    if score.values() > THRESHOLD:
        adding.append(score.keys())
    elif score.keys() in deployed_regions:
        removing.append(score.keys())

gcp_commands.orchestrate(adding, removing)

with open('utils/deployed_regions.json', 'w') as file:
    json.dump(adding, file)


regions = get_deployed_regions()
