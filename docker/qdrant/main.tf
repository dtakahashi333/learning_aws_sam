terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "qdrant" {
  name = "qdrant/qdrant:v1.17.1"
}

resource "docker_volume" "qdrant_storage" {
  name = "qdrant_storage"
}

resource "docker_container" "qdrant" {
  name  = "qdrant"
  image = docker_image.qdrant.name

  restart = "unless-stopped"

  ports {
    internal = 6333
    external = 6333
  }

  ports {
    internal = 6334
    external = 6334
  }

  mounts {
    source = docker_volume.qdrant_storage.name
    target = "/qdrant/storage"
    type   = "volume"
  }

  env = [
    "QDRANT__SERVICE__HTTP_PORT=6333",
    "QDRANT__SERVICE__GRPC_PORT=6334"
  ]

  healthcheck {
    test     = ["CMD-SHELL", "curl -f http://localhost:6333/collections || exit 1"]
    interval = "10s"
    retries  = 5
  }
}
