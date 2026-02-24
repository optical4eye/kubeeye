#!/bin/bash
# LDAP Initialization Script
# This script waits for OpenLDAP to start and applies the bootstrap LDIF

set -e

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

echo "Checking if LDAP needs initialization..."
existing_entries=$(ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "dc=kubeeye,dc=local" "(objectClass=*)" dn 2>/dev/null | grep -c "^dn:" || echo "0")

if [ "$existing_entries" -gt 0 ]; then
    echo "LDAP already initialized ($existing_entries entries found), skipping..."
    exit 0
fi

echo "Applying bootstrap LDIF..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" \
    -D "${LDAP_ADMIN_DN}" \
    -w "${LDAP_ADMIN_PASSWORD}" \
    -f "${LDIF_FILE}"

if [ $? -eq 0 ]; then
    echo "LDAP initialization completed successfully!"
else
    echo "ERROR: Failed to apply LDIF"
    exit 1
fi
