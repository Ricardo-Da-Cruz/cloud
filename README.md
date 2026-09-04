Decentralized Virtual CDN (Cloud Computing Lab Project)

Summary
-------
This repository is an implementation for a lab assignment: a decentralized virtual CDN with opportunistic offloading built on Google Cloud. It includes an orchestrator that decides where to deploy edge caching groups, an edge node listener used by edge VMs, a simple server-scoring module to place caches close to users, and helper scripts to configure GCP networking.

Key components
--------------
- src/orquestrator.py: Main autoscaler/orchestrator. Reads region prices and deployed regions, gathers server scores and decides which regions to add/remove, then calls the GCP orchestration helpers.
- src/gcp_commands.py: Helpers that wrap gcloud commands to create/delete managed instance groups, configure autoscaling, NAT/router, and list deployed instance-groups.
- src/server_score_calculator.py: Computes server "scores" from recent client IPs (reads /var/log/nginx/bucket_access.log) and geolocates IPs to weight regions.
- src/edge_server_listener.py: TCP listener used on edge servers to exchange/collect server scores between peers.
- src/enable_private_google_access.py: Enables Private Google Access on subnets so VMs can access GCS without external IPs.
- nginx.conf: Example NGINX configuration for an edge caching node (serves from mounted GCS bucket and logs to /var/log/nginx/*).
- Dockerfile: Builds an image that installs gcloud and runs the orchestrator (expects service account key at src/utils/key.json).
- cloud_computing_lab_project.pdf: Final report and architecture description (finds detailed design, cost analysis and predictive model there).

Prerequisites / Configuration
-----------------------------
1. Place a Google service account JSON key at src/utils/key.json and set PROJECT_ID in source files if different from the hardcoded value.
2. Install gcloud SDK (required by gcp_commands wrapper), and authenticate if running locally.
3. Python 3.8+ and dependencies: pip install -r requirements.txt
4. Edge VMs should mount a GCS bucket (or provide /mnt/gcp-bucket) and run nginx using the provided nginx.conf. NGINX must log to /var/log/nginx/bucket_access.log.

How it works (high level)
-------------------------
- Edge nodes run a small TCP listener (edge_server_listener) that responds to score queries and exchanges local server scores with other nodes on the private network.
- server_score_calculator reads recent client IPs from the NGINX access log, geolocates them (ip-api.com batch), and computes a score per GCP region.
- orquestrator collects scores across deployed regions, combines them with per-region price data (src/utils/prices.json) and decides which regions to scale up or down.
- gcp_commands implements the concrete operations using gcloud commands (create managed instance groups, set autoscaling, add/remove backends, create NAT/router).

Running locally (development)
-----------------------------
- Install deps: pip install -r requirements.txt
- Start an edge listener (on an edge VM or locally for testing):
  python src/edge_server_listener.py
- Run the orchestrator (requires gcloud and service account key):
  python src/orquestrator.py

Docker
------
Build image (this image expects the service-account key to already be copied into src/utils/key.json):
  docker build -t cdn-orchestrator .
Run (example):
  docker run --rm -v $PWD/src/utils/key.json:/usr/src/app/key.json cdn-orchestrator

Notes, limitations and TODOs
---------------------------
- Many values are hardcoded (PROJECT_ID, service account path, image/template names). Update them before production use.
- gcp_commands uses the local gcloud binary — container or host must have gcloud available for those functions to work.
- ip geolocation uses ip-api.com free batch endpoint — rate limits and privacy implications apply.
- The orchestrator and helpers need valid permissions and network access to GCP APIs and private networks.
- The project assumes no TLS for bootstrapping (assignment requirement) and uses private IPs for inter-node communication.

Where to read more
------------------
- See cloud_computing_lab_project.pdf for architecture diagrams, cost analysis, predictive model details and the project's full report.

Contact / author
----------------
This repository was created to fulfil the assignment described in assignment.pdf. Adjust configuration values in src/ before running.
