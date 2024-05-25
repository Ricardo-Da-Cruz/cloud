import json
import re
from collections import deque

import numpy as np
import requests
from google.oauth2 import service_account
from googleapiclient import discovery

SERVICE_ACCOUNT_FILE = 'utils/key.json'
PROJECT_ID = 'glassy-droplet-304915'
IMAGE_NAME = 'caching-server-image'
INSTANCE_NAME = 'new-instance-name'

CREDENTIALS = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/cloud-platform'])

SERVICE = discovery.build('compute', 'v1', credentials=CREDENTIALS)


def calculate_distance(coord1, coord2):
    return np.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)


def assign_server_scores(customers, servers):
    server_coordinates = list(servers.values())
    server_keys = list(servers.keys())

    scores = {}

    for key in server_keys:
        scores[key] = 0

    for customer in customers:
        distances = [calculate_distance(customer, server) for index, server in enumerate(server_coordinates)]

        sorted_indices = np.argsort(distances)

        for rank, idx in enumerate(sorted_indices):
            server_key = server_keys[idx]
            scores[server_key] += (1 / (rank + 1) ** 2)  # Weighted current votes

    return scores


def get_server_coords():
    with open('utils/gcp_region.json', 'r') as file:
        data = json.load(file)

    return {region: (details["latitude"], details["longitude"]) for region, details in data.items()}


def get_previous_server_scores():
    file = open('utils/server_scores', 'r')
    server_scores = json.load(file)
    file.close()

    return server_scores


def get_server_scores():
    ips = get_ips_from_nginx()

    coords = ip_to_geolocation(ips)

    server_coords = get_server_coords()

    return assign_server_scores(coords, server_coords)


def ip_to_geolocation(ip_addresses):
    fields = ['lat', 'lon']
    try:
        response = requests.post(f"http://ip-api.com/batch?fields={','.join(fields)}", json=ip_addresses)
        response.raise_for_status()
    except requests.RequestException as err:
        print(f"Request failed: {err}")
        return []

    data = response.json()
    results = []
    for item in data:
        results.append(tuple(item.get(field, None) for field in fields))

    return results


def get_ips_from_nginx():
    ip_regex = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    exclusion_string = "GoogleHC/1.0"
    unique_ips = set()
    ip_list = deque(maxlen=100)

    with open('/var/log/nginx/bucket_access.log', 'r') as file:
        for line in reversed(list(file)):
            if exclusion_string in line:
                continue
            match = re.search(ip_regex, line)
            if match:
                ip = match.group()
                if ip not in unique_ips:
                    unique_ips.add(ip)
                    ip_list.appendleft(ip)
                    if len(ip_list) >= 100:
                        break

    return list(ip_list)
