import json
import re

import numpy as np
import requests
from google.oauth2 import service_account
from googleapiclient import discovery

import gcp_orchestrator

SERVICE_ACCOUNT_FILE = 'utils/glassy-droplet-304915-566e6b23c2b2.json'
PROJECT_ID = 'glassy-droplet-304915'
IMAGE_NAME = 'caching-server-image'
INSTANCE_NAME = 'new-instance-name'

CREDENTIALS = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/cloud-platform'])

SERVICE = discovery.build('compute', 'v1', credentials=CREDENTIALS)


def calculate_distance(coord1, coord2):
    return np.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)


def assign_server_scores(customers, servers, previous_votes, weight=0.25):
    server_coordinates = list(servers.values())
    server_keys = list(servers.keys())

    # Apply weight to previous votes
    for key in previous_votes:
        previous_votes[key] *= weight

    for customer in customers:
        distances = [calculate_distance(customer, server) for index, server in enumerate(server_coordinates)]

        sorted_indices = np.argsort(distances)

        for rank, idx in enumerate(sorted_indices):
            server_key = server_keys[idx]
            previous_votes[server_key] += (1 / (rank + 1) ** 2) * (1 - weight)  # Weighted current votes

    return previous_votes


def get_server_coords():
    with open('deployed_zones.json', 'r') as file:
        data = json.load(file)

    return {region: (details["latitude"], details["longitude"]) for region, details in data.items()}


def get_server_scores_from_servers(ips):
    #TODO
    print("fdvbndjbd")


def send_server_scores_to_server(ip):
    #TODO
    print("fedgs")


def ip_to_geolocation(ip_address):
    fields = ['lat', 'lon']
    try:
        response = requests.get(f"https://ip-api.com/json/{ip_address}?fields={','.join(fields)}")
        response.raise_for_status()
    except requests.RequestException as err:
        print(f"Request failed: {err}")
        return None

    data = response.json()
    return data['lat'], data['lon']


def get_ips_from_nginx():
    ip_regex = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

    ips = []

    with open('/var/log/nginx/access.log', 'r') as file:
        for line in file:
            match = re.search(ip_regex, line)
            if match:
                ips.append(match)

    return ips


if __name__ == "__main__":
    gcp_orchestrator.add_caching_server("us-west4-b", 'network-lb')

    with open('utils/gcp_regions.json', 'r') as file:
        regions = json.load(file)
