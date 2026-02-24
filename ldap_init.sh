#!/bin/bash
# LDAP Initialization Script
# This script waits for OpenLDAP to start and applies the bootstrap LDIF
# Since LDAP data is not persisted, this runs on every container restart

LDAP_HOST="${LDAP_HOST:-openldap}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-cn=admin,dc=kubeeye,dc=local}"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin}"
LDIF_FILE="${LDIF_FILE:-/ldif/50-bootstrap.ldif}"

echo "Waiting for OpenLDAP to start..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "" -s base "(objectclass=*)" > /dev/null 2>&1; then
        echo "OpenLDAP is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "Attempt $attempt/$max_attempts: OpenLDAP not ready yet, waiting..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: OpenLDAP did not start within timeout"
    exit 1
fi

# Function to check if specific user exists (with authentication)
check_user_exists() {
    local user_dn="$1"
    ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" \
        -D "${LDAP_ADMIN_DN}" \
        -w "${LDAP_ADMIN_PASSWORD}" \
        -b "$user_dn" -s base "(objectClass=*)" dn 2>/dev/null | grep -q "^dn:"
}

# Check if already initialized
echo "Checking if LDAP is already initialized..."
if check_user_exists "uid=ldapadmin,ou=users,dc=kubeeye,dc=local"; then
    echo "LDAP already initialized, skipping..."
    exit 0
fi

echo "LDAP needs initialization..."

# Apply LDIF with retry (use -c to continue on "already exists" errors)
max_retries=5
retry=0

while [ $retry -lt $max_retries ]; do
    echo "Applying bootstrap LDIF (attempt $((retry + 1))/$max_retries)..."

    # Use -c to continue on errors like "already exists"
    output=$(ldapadd -x -c -H "ldap://${LDAP_HOST}:${LDAP_PORT}" \
        -D "${LDAP_ADMIN_DN}" \
        -w "${LDAP_ADMIN_PASSWORD}" \
        -f "${LDIF_FILE}" 2>&1)

    # Check if there were any real errors (not just "already exists")
    if echo "$output" | grep -q "adding new entry"; then
        echo "$output"
        echo "LDIF applied successfully!"
        break
    elif echo "$output" | grep -v "Already exists" | grep -q "ldap_add:"; then
        echo "$output"
        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            echo "Failed to apply LDIF, retrying in 3 seconds..."
            sleep 3
        else
            echo "ERROR: Failed to apply LDIF after all retries"
            exit 1
        fi
    else
        echo "$output"
        echo "Entries already exist, skipping..."
        break
    fi
done

# Verify initialization
echo "Verifying LDAP initialization..."
sleep 1

if check_user_exists "uid=ldapadmin,ou=users,dc=kubeeye,dc=local"; then
    echo "LDAP initialization completed successfully!"
    exit 0
else
    echo "WARNING: User 'ldapadmin' was not found"
    exit 1
fi
