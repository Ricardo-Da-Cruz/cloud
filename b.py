from google.oauth2 import service_account
from googleapiclient.discovery import build


PROJECT_ID = 'glassy-droplet-304915'
VPC_NETWORK = 'default'
SERVICE_ACCOUNT_FILE = 'utils/glassy-droplet-304915-566e6b23c2b2.json'
# this script enables private google access to every region subnet so that the vms can have access to the bucket without
# needing an external IP address. This can save on the billing for external IPs for the VMs


def enable_private_google_access(project_id, vpc_network, service_account_file):
    credentials = service_account.Credentials.from_service_account_file(service_account_file)
    service = build('compute', 'v1', credentials=credentials)

    request = service.subnetworks().aggregatedList(project=project_id)
    response = request.execute()

    for region, subnetworks in response['items'].items():
        for subnetwork in subnetworks.get('subnetworks', []):
            if subnetwork['network'].endswith(vpc_network):
                if not subnetwork['privateIpGoogleAccess']:
                    subnetwork_name = subnetwork['name']
                    print(f"Enabling Private Google Access for subnet: {subnetwork_name} in region: {region}")

                    request = service.subnetworks().setPrivateIpGoogleAccess(
                        project=project_id,
                        region=region.split('/')[-1],
                        subnetwork=subnetwork_name,
                        body={
                            'privateIpGoogleAccess': True
                        }
                    )
                    response = request.execute()
                    print(f"Private Google Access enabled for subnet: {subnetwork_name} in region: {region}")
                else:
                    print(f"Private Google Access already enabled for subnet: {subnetwork['name']} in region: {region}")

if __name__ == '__main__':
    enable_private_google_access(PROJECT_ID, VPC_NETWORK, SERVICE_ACCOUNT_FILE)
