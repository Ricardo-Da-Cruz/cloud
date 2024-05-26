import json
from concurrent import futures

import gcp_commands
import server_score_calculator
from edge_server_listener import get_server_scores_from_servers
from google.cloud import storage
from google.oauth2 import service_account

THRESHOLD = 12


def get_deployed_regions():
    bucket_name = 'orchestrator-utils'
    blob_name = 'deployed_regions.json'

    credentials = service_account.Credentials.from_service_account_file("utils/key.json")

    client = storage.Client(credentials=credentials, project="glassy-droplet-304915")

    # Get the bucket and blob
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    content = blob.download_as_text()

    data = json.loads(content)

    return data


def upload_deployed_regions(data):
    bucket_name = 'orchestrator-utils'
    blob_name = 'deployed_regions.json'

    credentials = service_account.Credentials.from_service_account_file("utils/key.json")

    client = storage.Client(credentials=credentials, project="glassy-droplet-304915")

    # Get the bucket and blob
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Convert the data back to JSON and upload it
    content = json.dumps(data, indent=2)
    blob.upload_from_string(content, content_type='application/json')


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
    if score > THRESHOLD:
        adding.append(score.keys())
    elif region in deployed_regions:
        removing.append(region)

deployed = [item for item in deployed_regions if item not in removing]

if not deployed:
    adding.append(max(scores, key=scores.get))

deployed.append(adding)
upload_deployed_regions(deployed)

print("adding: " + str(adding))
print("removing: " + str(removing))

gcp_commands.orchestrate(adding, removing)

regions = get_deployed_regions()
