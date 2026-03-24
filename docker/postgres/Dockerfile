# 1. Build the image:
#   docker build -t sam-postgres .
# 2. Run the container
#   docker run -v pgdata:/var/lib/postgresql/data -p 5432:5432 -d sam-postgres # pgdata is a Docker-managed named volume. Docker decides the physical path.

# Use the official PostgreSQL image as base
FROM postgres:17.9-trixie

# Copy optional SQL initialization scripts into container
# Any .sql or .sh scripts in /docker-entrypoint-initdb.d/ will run at container startup
COPY init-db.sql /docker-entrypoint-initdb.d/

# Expose the default PostgreSQL port
EXPOSE 5432