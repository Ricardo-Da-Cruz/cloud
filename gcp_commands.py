import json
import subprocess

import requests
from google.oauth2 import service_account
from googleapiclient import discovery

import concurrent.futures

SERVICE_ACCOUNT_FILE = 'utils/glassy-droplet-304915-566e6b23c2b2.json'
PROJECT_ID = 'glassy-droplet-304915'
IMAGE_NAME = 'caching-server-image'
INSTANCE_NAME = 'new-instance-name'
BACKEND_SERVICE_NAME = 'network-lb'
CACHING_SERVER_TEMPLATE = 'caching-server-template'

CREDENTIALS = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/cloud-platform'])

SERVICE = discovery.build('compute', 'v1', credentials=CREDENTIALS)


def run_gcloud_command(command):
    try:
        print("executing command:")
        print(" ".join(command))
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


def get_zones_in_region(region):
    command = [
        'gcloud', 'compute', 'regions', 'describe', region,
        '--format=json'
    ]
    output = run_gcloud_command(command)
    if output:
        region_info = json.loads(output)
        zones = region_info.get('zones', [])
        zone_names = [zone.split('/')[-1] for zone in zones]
        return ",".join(zone_names)
    return []


def create_managed_instance_group(instance_group_name, region, size=1,
                                  health_check='scaling-group-health-check',
                                  min_replicas=1, max_replicas=10, cpu_utilization=0.8):
    zones = get_zones_in_region(region)

    print(f"zones: {zones}")

    command = [
        'gcloud', 'compute', 'instance-groups', 'managed', 'create', instance_group_name,
        f'--project={PROJECT_ID}',
        f'--base-instance-name={instance_group_name}',
        f'--template={CACHING_SERVER_TEMPLATE}',
        f'--size={size}',
        f'--zones={zones}',
        '--target-distribution-shape=EVEN',
        '--instance-redistribution-type=PROACTIVE',
        '--default-action-on-vm-failure=repair',
        f'--health-check={health_check}',
        '--initial-delay=300',
        '--no-force-update-on-repair',
        '--list-managed-instances-results=PAGELESS'
    ]

    print(command)

    output = run_gcloud_command(command)

    if output:
        print(f"Managed instance group {instance_group_name} created successfully.")
    else:
        print(f"Failed to create managed instance group {instance_group_name}.")
        return

    # Set autoscaling for the managed instance group
    autoscaling_command = [
        'gcloud', 'compute', 'instance-groups', 'managed', 'set-autoscaling', instance_group_name,
        f'--project={PROJECT_ID}',
        f'--region={region}',
        '--mode=on',
        f'--min-num-replicas={min_replicas}',
        f'--max-num-replicas={max_replicas}',
        f'--target-cpu-utilization={cpu_utilization}',
        '--cool-down-period=120'
    ]

    autoscaling_output = run_gcloud_command(autoscaling_command)
    if autoscaling_output:
        print(f"Autoscaling set for managed instance group {instance_group_name} successfully.")
    else:
        print(f"Failed to set autoscaling for managed instance group {instance_group_name}.")

    # Add the instance group to the load balancer backend service
    add_command = [
        'gcloud', 'compute', 'backend-services', 'add-backend', BACKEND_SERVICE_NAME,
        '--project', PROJECT_ID,
        '--global',
        '--instance-group', instance_group_name,
        '--instance-group-region', region
    ]
    add_output = run_gcloud_command(add_command)
    if add_output:
        print(
            f"Managed instance group {instance_group_name} added to backend service {BACKEND_SERVICE_NAME} successfully.")
    else:
        print(f"Failed to add managed instance group {instance_group_name} to backend service {BACKEND_SERVICE_NAME}.")


def remove_instance_group_from_backend_service(instance_group_name, region):
    remove_command = [
        'gcloud', 'compute', 'backend-services', 'remove-backend', BACKEND_SERVICE_NAME,
        '--project', PROJECT_ID,
        '--global',
        '--instance-group', instance_group_name,
        '--instance-group-region', region,
        '--quiet'
    ]
    remove_output = run_gcloud_command(remove_command)
    if remove_output:
        print(
            f"Managed instance group {instance_group_name} removed from backend service {BACKEND_SERVICE_NAME} successfully.")
    else:
        print(
            f"Failed to remove managed instance group {instance_group_name} from backend service {BACKEND_SERVICE_NAME}.")


def delete_managed_instance_group(instance_group_name, region):
    remove_instance_group_from_backend_service(instance_group_name, region)
    delete_command = [
        'gcloud', 'compute', 'instance-groups', 'managed', 'delete', instance_group_name,
        '--project', PROJECT_ID,
        '--region', region,
        '--quiet'
    ]
    delete_output = run_gcloud_command(delete_command)
    if delete_output:
        print(f"Managed instance group {instance_group_name} deleted successfully.")
    else:
        print(f"Failed to delete managed instance group {instance_group_name}.")


def orchestrate(new_servers, old_servers):
    adding = [item for item in new_servers if item not in old_servers]
    removing = [item for item in old_servers if item not in new_servers]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Schedule the adding tasks
        add_futures = [
            executor.submit(
                create_managed_instance_group,
                f"cdn-{group}",
                group,  # Assuming region is the same as group for demonstration
                size=1,
                health_check='scaling-group-health-check',
                min_replicas=1,
                max_replicas=10,
                cpu_utilization=0.8
            )
            for group in adding
        ]

        for future in concurrent.futures.as_completed(add_futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred: {e}")

        remove_futures = [executor.submit(delete_managed_instance_group, "cdn-" + group, group) for group in removing]
