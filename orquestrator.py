import json
from concurrent import futures

import gcp_commands
from edge_server_listener import get_server_scores_from_servers


def get_deployed_regions():
    with open('utils/deployed_regions.json', 'r') as file:
        data = json.load(file)

    return data


regions = get_deployed_regions()

ips = ["35.219.166.30"]

# with futures.ThreadPoolExecutor() as executor:
#     results = [executor.submit(gcp_commands.get_vm_ips, region) for region in regions]
#
# for future in futures.as_completed(results):
#     result = future.result()
#     if result:
#         ips.append(result[0])


try:
    scores = get_server_scores_from_servers(ips, "scores_in_region", {})
except TimeoutError:
    print("Timeout detected. Performing TCP dump for further analysis.")
    perform_tcp_dump(duration=30, output_file="tcpdump_timeout")

