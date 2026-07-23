#!/usr/bin/env bash

set -euo pipefail

CONTAINER="passthrough_replicator_kafka"
BOOTSTRAP_SERVER="localhost:9094"
PARTITIONS=2

recreate_topic() {
  local topic="$1"

  echo "Deleting topic: ${topic}"

  docker exec "${CONTAINER}" \
    kafka-topics.sh \
    --topic "${topic}" \
    --delete \
    --if-exists \
    --bootstrap-server "${BOOTSTRAP_SERVER}"

  echo "Waiting for topic deletion: ${topic}"

  while docker exec "${CONTAINER}" \
    kafka-topics.sh \
    --topic "${topic}" \
    --describe \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    >/dev/null 2>&1
  do
    sleep 1
  done

  echo "Creating topic: ${topic}"

  docker exec "${CONTAINER}" \
    kafka-topics.sh \
    --topic "${topic}" \
    --create \
    --if-not-exists \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --partitions "${PARTITIONS}"

  echo "Recreated topic: ${topic}"
}

recreate_topic "events"
recreate_topic "events-replicated"

echo "All topics have been recreated."