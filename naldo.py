import json
import logging
import os
import re
import subprocess
from math import radians, sin, cos, sqrt, atan2

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


##################################### REQUEST MONITORING #####################################

def closest_region(lat, lon):
    # Load the deployed zones data from the deployed_zones.json file
    with open('deployed_zones.json', 'r') as file:
        deployed_zones = json.load(file)

    # Convert the given latitude and longitude to radians
    lat = radians(lat)
    lon = radians(lon)

    # Initialize the minimum distance and closest region
    min_distance = float('inf')
    nearest_region = None

    # Iterate over each deployed zone
    for zone, data in deployed_zones.items():
        # Convert the zone's latitude and longitude to radians
        zone_lat = radians(data['latitude'])
        zone_lon = radians(data['longitude'])

        # Calculate the differences
        diff_lat = lat - zone_lat
        diff_lon = lon - zone_lon

        # Calculate the distance using the Haversine formula
        a = sin(diff_lat / 2)**2 + cos(zone_lat) * cos(lat) * sin(diff_lon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c  # Radius of the Earth is 6371 kilometers

        # Check if the distance is less than the minimum distance and within the radius
        if distance < min_distance and distance <= 500:
            min_distance = distance
            nearest_region = zone

    # If a nearby region was found, return it
    if nearest_region is not None:
        return nearest_region

    # If no nearby region was found, return None
    return None





def is_ip_nearby(lat, lon):
    # Load the deployed zones data from the deployed_zones.json file
    with open('deployed_zones.json', 'r') as file:
        deployed_zones = json.load(file)

    # Convert the given latitude and longitude to radians
    lat = radians(lat)
    lon = radians(lon)

    # Iterate over each deployed zone
    for zone, data in deployed_zones.items():
        # Convert the zone's latitude and longitude to radians
        zone_lat = radians(data['latitude'])
        zone_lon = radians(data['longitude'])

        # Calculate the differences
        diff_lat = lat - zone_lat
        diff_lon = lon - zone_lon

        # Calculate the distance using the Haversine formula
        a = sin(diff_lat / 2) ** 2 + cos(zone_lat) * cos(lat) * sin(diff_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c  # Radius of the Earth is 6371 kilometers

        # Check if the distance is less than or equal to the radius
        if distance <= 500:
            return True

    # If no nearby zone was found, return False
    return False


def check_ip_outliers():
    # Get the list of IP addresses from the log file
    with open('ip_addresses.log', 'r') as file:
        ip_addresses = file.readlines()

    # Count the occurrences of each IP address
    counts = {}
    for ip in ip_addresses:
        ip = ip.strip()
        if ip in counts:
            counts[ip] += 1
        else:
            counts[ip] = 1

    # Find the IP addresses that are furthest from the mean
    lat, lon = ip_to_geolocation(ip)

    outliers = {}
    regions = []

    if not is_ip_nearby(lat, lon):
        outliers[ip] = [
            lat, lon]
    for [lat, lon] in outliers:
        region = closest_region(lat, lon)
        if region is not None:
            regions.append(region)
        # else ignore this outlier

    return outliers


def check_nginx_logs():
    # Define the log format
    log_format = '%(message)s'

    # Configure the logging module
    logging.basicConfig(filename='ip_addresses.log', level=logging.INFO, format=log_format)

    # Define the regular expression for an IP address
    ip_regex = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

    # Open the Nginx access log file
    with open('/var/log/nginx/access.log', 'r') as file:
        for line in file:
            # Search for an IP address in the line
            match = re.search(ip_regex, line)
            if match:
                # If an IP address is found, log it
                logging.info(match.group())

    print("IP addresses have been written to ip_addresses.log.")


################################### END REQUEST MONITORING ###################################

def run_gcloud_command(command):
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}")
        return None
    except FileNotFoundError as e:
        print(f"gcloud command not found: {e}")
        return None


def check_instance_group_exists(project_id, zone, instance_group_name):
    command = [
        'gcloud', 'compute', 'instance-groups', 'list',
        '--project', project_id,
        '--zones', zone,
        '--format=json'
    ]
    output = run_gcloud_command(command)
    if output:
        groups = json.loads(output)
        for group in groups:
            if group['name'] == instance_group_name:
                return True
    return False


def create_instance_group(project_id, zone, instance_group_name, backend_service_name):
    command = [
        'gcloud', 'compute', 'instance-groups', 'unmanaged', 'create', instance_group_name,
        '--project', project_id,
        '--zone', zone
    ]
    run_gcloud_command(command)

    command = [
        'gcloud', 'compute', 'backend-services', 'add-backend', backend_service_name,
        '--project', project_id,
        '--instance-group', instance_group_name,
        '--instance-group-zone', zone,
        '--global'
    ]
    run_gcloud_command(command)


def add_instance_to_group(project_id, zone, instance_group_name, instance_name):
    command = [
        'gcloud', 'compute', 'instance-groups', 'unmanaged', 'add-instances', instance_group_name,
        '--project', project_id,
        '--zone', zone,
        '--instances', instance_name
    ]
    run_gcloud_command(command)


def create_instance_from_image(project_id, zone, instance_name, machine_image_name, service_account_file):
    # Set the environment variable for authentication
    env = {
        **os.environ,
        'GOOGLE_APPLICATION_CREDENTIALS': service_account_file
    }

    command = [
        'gcloud', 'compute', 'instances', 'create', instance_name,
        '--project', project_id,
        '--zone', zone,
        '--source-machine-image', machine_image_name,
        '--no-address'
    ]

    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
        print("Instance created successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while creating the instance: {e.stderr}")


def add_caching_server(zone, lb_name):
    instance_group_name = "caching-group-" + zone
    instance_name = "caching-server-" + zone

    create_instance_from_image(PROJECT_ID, zone, instance_name, "caching-server-image",
                               SERVICE_ACCOUNT_FILE)

    if not check_instance_group_exists(PROJECT_ID, zone, instance_group_name):
        create_instance_group(PROJECT_ID, zone, instance_group_name, lb_name)

    add_instance_to_group(PROJECT_ID, zone, instance_group_name, instance_name)

    with open('utils/gcp_regions.json', 'r') as file:
        regions = json.load(file)

    region = zone.rsplit('-', 1)[0]

    if region in regions:
        with open('deployed_zones.json', 'r') as file:
            deployed_zones = json.load(file)

        if region not in deployed_zones:
            deployed_zones[region] = regions[region]
            deployed_zones[region]['counter'] = 1  # Initialize the counter
        else:
            deployed_zones[region]['counter'] += 1

        with open('deployed_zones.json', 'w') as file:
            json.dump(deployed_zones, file)


# Example usage
if __name__ == "__main__":
    add_caching_server("us-west4-b", 'network-lb')
