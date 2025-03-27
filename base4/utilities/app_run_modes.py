app_run_modes = [
    'docker',               # Standard Docker installation with each service running in a separate container
    'docker-monolith',      # Dev Docker installation where all services run as a monolithic application inside a single container
    'linux-micro-services',        # All services running locally in separate processes
    'linux-monolith',              # All services running in a single monolithic process
    'macos-micro-services',        # All services running locally in separate processes
    'macos-monolith'               # All services running in a single monolithic process
]

app_environments = [
    'ch',
    'prod',
    'stage',
    'stage2',
    'dev',
    'dev-igor',
    'dev-sloba'
]
