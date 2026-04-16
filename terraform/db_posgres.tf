terraform {
  required_version = ">= 1.14.7, < 2.0.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Password for the PostgreSQL database"
}

# Pull image with platform constraint
resource "docker_image" "postgres" {
  name         = "postgres:17.9-trixie"
  keep_locally = true

  # Forces x86_64 like docker-compose
  platform = "linux/amd64"
}

# Named volume (pgdata)
resource "docker_volume" "pgdata" {
  name = "pgdata"
}

resource "docker_container" "db" {
  name  = "sam-postgres"
  image = docker_image.postgres.name

  restart = "always"

  ports {
    internal = 5432
    external = 5432
  }

  env = [
    "POSTGRES_DB=sam_chatbot",
    "POSTGRES_USER=sam_user",
    "POSTGRES_PASSWORD=${var.db_password}"
  ]

  # Named volume (persistent data)
  mounts {
    target = "/var/lib/postgresql/data"
    source = docker_volume.pgdata.name
    type   = "volume"
  }

  # Init script (read-only bind mount)
  mounts {
    target    = "/docker-entrypoint-initdb.d/init-db.sql"
    source    = abspath("${path.module}/init-db.sql")
    type      = "bind"
    read_only = true
  }
}
