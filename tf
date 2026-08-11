#!/bin/bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v "$HOME/.aws":/root/.aws:ro \
  -w /workspace \
  hashicorp/terraform:1.9.8 "$@"
