app_run_modes = [
    'docker',               # Standard Docker installation with each service running in a separate container
    'docker-monolith',      # Dev Docker installation where all services run as a monolithic application inside a single container
    'micro-services',       # All services running locally in separate processes
    'monolith'              # All services running in a single monolithic process
]