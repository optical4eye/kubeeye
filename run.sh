#!/bin/bash

# Get machine IP address (works on Linux, Mac, and Windows with Git Bash)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows - get IP using PowerShell (more reliable than ipconfig parsing)
    MACHINE_IP=$(powershell.exe -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.IPAddress -notlike '127.*' -and \$_.IPAddress -notlike '169.254.*' } | Select-Object -First 1).IPAddress" 2>/dev/null || echo "")
    # Fallback to ipconfig if PowerShell fails
    if [ -z "$MACHINE_IP" ]; then
        MACHINE_IP=$(ipconfig | grep -i "ipv4" | head -1 | sed 's/.*: //' | tr -d '\r')
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # MacOS
    MACHINE_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
else
    # Linux
    MACHINE_IP=$(hostname -I | awk '{print $1}')
fi

# Fallback to localhost if IP detection fails
if [ -z "$MACHINE_IP" ]; then
    echo "Warning: Could not detect machine IP, using localhost"
    MACHINE_IP="localhost"
fi

echo "Detected machine IP: $MACHINE_IP"
echo "OSTYPE: $OSTYPE"

# Function to replace text in file (works on all platforms)
replace_in_file() {
    local file="$1"
    local search="$2"
    local replace="$3"

    # Use sed with temporary file (compatible with Git Bash on Windows)
    sed "s|$search|$replace|g" "$file" > "$file.tmp"
    if [ $? -eq 0 ]; then
        mv "$file.tmp" "$file"
        echo "  ✓ Updated $file"
    else
        echo "  ✗ Failed to update $file"
        rm -f "$file.tmp"
    fi
}

# Update IP in docker-compose.yaml
echo "Updating docker-compose.yaml..."
replace_in_file "docker-compose.yaml" "http://localhost:5556/dex" "http://$MACHINE_IP:5556/dex"
replace_in_file "docker-compose.yaml" "http://localhost:3000/auth/callback" "http://$MACHINE_IP:3000/auth/callback"

# Update IP in dex-config.yaml
echo "Updating ldap_files/dex-config.yaml..."
replace_in_file "ldap_files/dex-config.yaml" "http://localhost:5556/dex" "http://$MACHINE_IP:5556/dex"
replace_in_file "ldap_files/dex-config.yaml" "http://localhost:3000/auth/callback" "http://$MACHINE_IP:3000/auth/callback"

# Verify the changes
echo ""
echo "Verifying changes:"
echo "--- docker-compose.yaml ---"
grep -E "KUBEEYE_OAUTH_ISSUER_URL|KUBEEYE_OAUTH_REDIRECT_URI" docker-compose.yaml | head -2
echo ""
echo "--- ldap_files/dex-config.yaml ---"
grep -E "issuer:|redirectURIs:" -A1 ldap_files/dex-config.yaml | head -4

# Remove any leftover files
rm -f docker-compose.yaml.bak ldap_files/dex-config.yaml.bak *.tmp ldap_files/*.tmp 2>/dev/null || true

echo "Configuration files updated with IP: $MACHINE_IP"

# Stop and remove all containers, then start fresh
# This ensures LDAP data is recreated on each run
docker-compose down -v
docker-compose up -d

# Rebuild and recreate backend and frontend
docker compose up --build --force-recreate --no-deps backend -d
docker compose up --build --force-recreate --no-deps frontend -d

echo ""
echo "Waiting for services to start..."
sleep 5

# Wait for OpenLDAP to be ready and load bootstrap data
echo ""
echo "Waiting for OpenLDAP to be ready..."
sleep 10

# Copy LDIF file into container
echo "Copying LDIF file to container..."
docker cp ldap_files/50-bootstrap.ldif kubeeye-openldap:/tmp/bootstrap.ldif

echo "Loading LDAP bootstrap data..."
LDAP_LOAD=$(docker exec kubeeye-openldap ldapadd -x -H ldap://localhost:389 -D "cn=admin,dc=kubeeye,dc=local" -w admin -f //tmp//bootstrap.ldif 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ OpenLDAP bootstrap data loaded successfully"
else
    # Check if data already exists (entry already exists error)
    if echo "$LDAP_LOAD" | grep -q "already exists"; then
        echo "✓ OpenLDAP bootstrap data already present"
    else
        echo "✗ OpenLDAP bootstrap data NOT loaded"
        echo "LDAP load output:"
        echo "$LDAP_LOAD"
    fi
fi

# Verify the data
echo ""
echo "Verifying LDAP data..."
LDAP_CHECK=$(docker exec kubeeye-openldap ldapsearch -x -H ldap://localhost:389 -D "cn=admin,dc=kubeeye,dc=local" -w admin -b "ou=users,dc=kubeeye,dc=local" "(objectClass=inetOrgPerson)" 2>&1)
if echo "$LDAP_CHECK" | grep -q "uid=ldapadmin"; then
    echo "✓ LDAP users verified (ldapadmin found)"
else
    echo "✗ LDAP users NOT found"
fi

echo ""
echo "=========================================="
echo "KubeEye is starting up..."
echo ""
echo "Access URLs:"
echo "  Frontend: http://$MACHINE_IP:3000"
echo "  Backend API: http://$MACHINE_IP:8000"
echo "  Dex (OAuth): http://$MACHINE_IP:5556/dex"
echo ""
echo "Test users:"
echo "  ldapadmin / ldapadmin123 (admin group)"
echo "  operator1 / operator123 (operator group)"
echo ""
echo "To check OpenLDAP logs:"
echo "  docker-compose logs openldap"
echo "=========================================="
