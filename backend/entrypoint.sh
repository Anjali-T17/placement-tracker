#!/bin/sh
set -e

# Ensure data directory exists
mkdir -p /app/data

# If database doesn't exist in the persistent volume yet, seed it with existing database if available
if [ ! -f /app/data/placement.db ] && [ -f /app/placement.db ]; then
    echo "Copying initial placement.db to persistent volume /app/data/placement.db..."
    cp /app/placement.db /app/data/placement.db
fi

# Execute the application
exec "$@"
