terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

provider "docker" {}

variable "db_password" {
  sensitive = true
}

resource "docker_image" "postgres" {
  name = "postgres:17.9-trixie"
}

resource "docker_container" "db" {
  name  = "sam-postgres"
  image = docker_image.postgres.name

  ports {
    internal = 5432
    external = 5432
  }

  env = [
    "POSTGRES_DB=sam_chatbot",
    "POSTGRES_USER=sam_user",
    "POSTGRES_PASSWORD=${var.db_password}"
  ]

  volumes {
    host_path      = abspath("${path.module}/init-db.sql")
    container_path = "/docker-entrypoint-initdb.d/init-db.sql"
  }
}
