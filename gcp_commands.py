import json
import subprocess

import requests
from google.oauth2 import service_account
from googleapiclient import discovery

SERVICE_ACCOUNT_FILE = 'utils/glassy-droplet-304915-566e6b23c2b2.json'
PROJECT_ID = 'glassy-droplet-304915'
IMAGE_NAME = 'caching-server-image'
INSTANCE_NAME = 'new-instance-name'

CREDENTIALS = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/cloud-platform'])

SERVICE = discovery.build('compute', 'v1', credentials=CREDENTIALS)


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


def create_instance_from_image(project_id, zone, instance_name, machine_image_name):
    command = [
        'gcloud', 'compute', 'instances', 'create', instance_name,
        '--project', project_id,
        '--zone', zone,
        '--source-machine-image', machine_image_name,
        '--no-address'
    ]

    run_gcloud_command(command)


def add_caching_server(zone, lb_name):
    instance_group_name = "caching-group-" + zone
    instance_name = "ricardo-instance"

    create_instance_from_image(PROJECT_ID, zone, instance_name, "caching-server-image")

    if not check_instance_group_exists(PROJECT_ID, zone, instance_group_name):
        create_instance_group(PROJECT_ID, zone, instance_group_name, lb_name)

    add_instance_to_group(PROJECT_ID, zone, instance_group_name, instance_name)


def get_vm_ips(project_id, region):
    try:
        command = [
            "gcloud", "compute", "instances", "list",
            "--project", project_id,
            "--filter=zone:(" + region + ")",
            "--format=json"
        ]

        result = run_gcloud_command(command)

        if result:
            return []

        instances = json.loads(result)

        ips = []
        for instance in instances:
            network_interfaces = instance.get('networkInterfaces', [])
            for interface in network_interfaces:
                access_configs = interface.get('accessConfigs', [])
                for config in access_configs:
                    ip = config.get('natIP')
                    if ip:
                        ips.append(ip)
                internal_ip = interface.get('networkIP')
                if internal_ip:
                    ips.append(internal_ip)

        return ips

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def get_gcp_region():
    # Define the URL for the metadata server
    metadata_server_url = "http://169.254.169.254/computeMetadata/v1/instance/zone"
    headers = {"Metadata-Flavor": "Google"}

    # Make a request to the metadata server to get the zone
    response = requests.get(metadata_server_url, headers=headers)
    if response.status_code == 200:
        zone = response.text
        # Extract the region from the zone
        region = '-'.join(zone.split('/')[-1].split('-')[:-1])
        return region
    else:
        raise Exception("Failed to retrieve the zone information from the metadata server")


print(get_vm_ips(PROJECT_ID, "us-west4"))
