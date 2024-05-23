import numpy as np

# Assuming calculate_distance function is defined elsewhere
def calculate_distance(coord1, coord2):
    return np.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)

def assign_server_scores(customers, servers, previous_votes, weight=0.25):
    server_coordinates = list(servers.values())
    server_keys = list(servers.keys())

    # Apply weight to previous votes
    for key in previous_votes:
        previous_votes[key] *= weight

    for customer in customers:
        distances = [calculate_distance(customer, server) for server in server_coordinates]

        sorted_indices = np.argsort(distances)

        for rank, idx in enumerate(sorted_indices):
            server_key = server_keys[idx]
            previous_votes[server_key] += (1 / ((rank + 1) ** 2)) * (1 - weight)  # Weighted current votes
            print((1 / ((rank + 1)**2)))

    return previous_votes

# Example usage with the region_coordinates dictionary
customers = [(34.0522, -118.2437), (40.7128, -74.0060)]  # Example customer coordinates
servers = {
    'asia-east1': (23.69781, 120.960515),
    'asia-east2': (22.396428, 114.109497),
    # ... (other servers)
    'us-west4': (36.1699, -115.1398),
    'us-east5': (12,43)
}
previous_votes = {region: 0 for region in servers}  # Initialize previous_votes with zeros

# Assign server scores
updated_votes = assign_server_scores(customers, servers, previous_votes)
print(updated_votes)