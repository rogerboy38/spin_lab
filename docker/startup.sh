#!/bin/bash
set -e

cd /workspace/development/frappe-bench

# Wait for MariaDB
echo "Waiting for MariaDB..."
while ! mysqladmin ping -h"${MARIADB_HOST}" --silent; do
    sleep 1
done
echo "MariaDB is ready!"

# Initialize bench if not already done
if [ ! -d "sites/${SITE_NAME}" ]; then
    echo "Creating new site: ${SITE_NAME}"
    bench new-site "${SITE_NAME}" \
        --mariadb-root-password root \
        --admin-password "${ADMIN_PASSWORD}" \
        --no-mariadb-socket
    
    echo "Installing slot_lab app..."
    bench --site "${SITE_NAME}" install-app slot_lab
    
    echo "Site created and app installed successfully!"
fi

# Set site config for redis
bench --site "${SITE_NAME}" set-config -g redis_cache "redis://${REDIS_CACHE}"
bench --site "${SITE_NAME}" set-config -g redis_queue "redis://${REDIS_QUEUE}"
bench --site "${SITE_NAME}" set-config -g redis_socketio "redis://${REDIS_SOCKETIO}"

# Execute the main command
exec "$@"
