import re
from collections import deque

ip_regex = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
exclusion_string = "GoogleHC/1.0"
unique_ips = set()
ip_list = deque(maxlen=100)

with open('bucket_access.log', 'r') as file:
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

print(unique_ips)