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
        --db-root-password root \
        --admin-password "${ADMIN_PASSWORD}" \
        --mariadb-user-host-login-scope='%'

    echo "Installing spin_lab app..."
    # app source is volume-mounted into apps/spin_lab
    if ! grep -q '^spin_lab$' sites/apps.txt 2>/dev/null; then
        ./env/bin/pip install -e apps/spin_lab
        echo "spin_lab" >> sites/apps.txt
    fi
    bench --site "${SITE_NAME}" install-app spin_lab
    
    echo "Site created and app installed successfully!"
fi

# Set site config for redis
bench --site "${SITE_NAME}" set-config -g redis_cache "redis://${REDIS_CACHE}"
bench --site "${SITE_NAME}" set-config -g redis_queue "redis://${REDIS_QUEUE}"
bench --site "${SITE_NAME}" set-config -g redis_socketio "redis://${REDIS_SOCKETIO}"

# Execute the main command
exec "$@"
