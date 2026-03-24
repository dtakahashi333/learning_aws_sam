# hello_world.app

## Run
To run the Lambda handlers, use any of the following commands:
```sh
# On Linux, you might need to use the host network:
sam local start-api --docker-network host
# Set environment variables when starting the Lambda handlers:
PG_HOST=<pg-host> PG_PORT=<pg-port> PG_USER=<pg-user> PG_PASSWORD=<pg-password> PG_DB=<pg-db> sam local start-api --host 0.0.0.0 --port 3000
# Read environment variables from env.json when starting the Lambda handlers:
sam local start-api --env-vars env.json --host 0.0.0.0 --port 3000
```
