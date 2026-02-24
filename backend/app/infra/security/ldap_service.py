#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP Service for authentication against OpenLDAP and Active Directory
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE, SIMPLE
from ldap3.core.exceptions import LDAPException, LDAPBindError
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LDAPUser:
    """LDAP user information"""
    username: str
    email: str
    display_name: str
    dn: str  # Distinguished Name
    groups: List[str]


class LDAPService:
    """
    LDAP authentication service supporting OpenLDAP and Active Directory
    """

    # Attribute mapping for different LDAP server types
    ATTRIBUTE_MAPPING = {
        "openldap": {
            "username": "uid",
            "email": "mail",
            "display_name": "cn",
            "group_member": "member",
            "group_name": "cn",
        },
        "ad": {
            "username": "sAMAccountName",
            "email": "mail",
            "display_name": "displayName",
            "group_member": "member",
            "group_name": "cn",
        }
    }

    def __init__(self):
        """Initialize LDAP service with settings"""
        self.enabled = settings.kubeeye_ldap_enabled
        self.server_url = settings.kubeeye_ldap_server_url
        self.use_ssl = settings.kubeeye_ldap_use_ssl
        self.bind_dn = settings.kubeeye_ldap_bind_dn
        self.bind_password = settings.kubeeye_ldap_bind_password
        self.base_dn = settings.kubeeye_ldap_base_dn
        self.group_base_dn = settings.kubeeye_ldap_group_base_dn
        self.admin_group = settings.kubeeye_ldap_admin_group
        self.operator_group = settings.kubeeye_ldap_operator_group
        self.user_filter_template = settings.kubeeye_ldap_user_filter
        self.ldap_type = settings.kubeeye_ldap_type.lower()
        self.ad_domain = settings.kubeeye_ldap_ad_domain

        # Get attribute mapping based on LDAP type
        self.attributes = self.ATTRIBUTE_MAPPING.get(self.ldap_type, self.ATTRIBUTE_MAPPING["openldap"])

    def _get_server(self) -> Server:
        """Create LDAP server connection"""
        return Server(
            self.server_url,
            use_ssl=self.use_ssl,
            get_info=ALL
        )

    def _get_connection(self, user_dn: str = None, password: str = None) -> Optional[Connection]:
        """
        Create LDAP connection

        Args:
            user_dn: User DN for binding (optional, uses service account if not provided)
            password: Password for binding

        Returns:
            Connection object or None if connection failed
        """
        try:
            server = self._get_server()

            # Use provided credentials or service account
            bind_dn = user_dn or self.bind_dn
            bind_password = password or self.bind_password

            # Choose authentication method based on LDAP type
            if self.ldap_type == "ad":
                # Active Directory often uses NTLM
                authentication = NTLM
            else:
                authentication = SIMPLE

            connection = Connection(
                server,
                user=bind_dn,
                password=bind_password,
                authentication=authentication,
                auto_bind=True
            )

            return connection
        except LDAPBindError as e:
            logger.error(f"LDAP bind failed: {e}")
            return None
        except LDAPException as e:
            logger.error(f"LDAP connection error: {e}")
            return None

    def _find_user(self, conn: Connection, username: str) -> Optional[Dict[str, Any]]:
        """
        Find user in LDAP directory

        Args:
            conn: LDAP connection
            username: Username to search for

        Returns:
            User entry dict or None if not found
        """
        try:
            # Build search filter
            search_filter = self.user_filter_template.format(username=username)

            # Search for user
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[self.attributes["username"], self.attributes["email"],
                           self.attributes["display_name"], "memberOf", "distinguishedName"]
            )

            if len(conn.entries) == 0:
                logger.warning(f"LDAP user not found: {username}")
                return None

            # Return first entry
            entry = conn.entries[0]
            return {
                "dn": entry.entry_dn,
                "username": str(getattr(entry, self.attributes["username"], username)),
                "email": str(getattr(entry, self.attributes["email"], "")),
                "display_name": str(getattr(entry, self.attributes["display_name"], username)),
                "groups": self._get_user_groups(entry)
            }
        except LDAPException as e:
            logger.error(f"LDAP search error: {e}")
            return None

    def _get_user_groups(self, entry) -> List[str]:
        """
        Get groups for user from LDAP entry

        Args:
            entry: LDAP entry

        Returns:
            List of group DNs
        """
        groups = []

        # For Active Directory, groups are in memberOf attribute
        if hasattr(entry, "memberOf"):
            member_of = entry.memberOf
            if member_of:
                groups = [str(g) for g in member_of.values]

        return groups

    def _get_groups_for_dn(self, conn: Connection, user_dn: str) -> List[str]:
        """
        Get groups for a user DN (for OpenLDAP)

        Args:
            conn: LDAP connection
            user_dn: User DN

        Returns:
            List of group DNs
        """
        try:
            # Search for groups containing this user as member
            search_filter = f"({self.attributes['group_member']}={user_dn})"

            conn.search(
                search_base=self.group_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[self.attributes["group_name"]]
            )

            return [entry.entry_dn for entry in conn.entries]
        except LDAPException as e:
            logger.error(f"LDAP group search error: {e}")
            return []

    def authenticate(self, username: str, password: str) -> Optional[LDAPUser]:
        """
        Authenticate user against LDAP

        Args:
            username: Username
            password: Password

        Returns:
            LDAPUser object if authentication successful, None otherwise
        """
        if not self.enabled:
            logger.warning("LDAP authentication is disabled")
            return None

        try:
            # First, find the user using service account
            conn = self._get_connection()
            if not conn:
                logger.error("Failed to connect to LDAP server")
                return None

            user_data = self._find_user(conn, username)
            conn.unbind()

            if not user_data:
                return None

            user_dn = user_data["dn"]

            # Now try to bind with user credentials
            user_conn = self._get_connection(user_dn, password)
            if not user_conn:
                logger.warning(f"LDAP authentication failed for user: {username}")
                return None

            user_conn.unbind()

            # Get groups (for OpenLDAP, we need to search separately)
            groups = user_data["groups"]
            if not groups and self.group_base_dn:
                conn = self._get_connection()
                if conn:
                    groups = self._get_groups_for_dn(conn, user_dn)
                    conn.unbind()

            logger.info(f"LDAP authentication successful for user: {username}")

            return LDAPUser(
                username=username,
                email=user_data["email"] or f"{username}@kubeeye.local",
                display_name=user_data["display_name"] or username,
                dn=user_dn,
                groups=groups
            )

        except LDAPException as e:
            logger.error(f"LDAP authentication error: {e}")
            return None

    def determine_role(self, groups: List[str]) -> Optional[str]:
        """
        Determine user role based on LDAP groups

        Args:
            groups: List of group DNs

        Returns:
            Role string ('admin' or 'operator') or None if not in any group
        """
        if not groups:
            return None

        # Check admin group first
        if self.admin_group:
            for group in groups:
                if self.admin_group.lower() in group.lower():
                    return "admin"

        # Check operator group
        if self.operator_group:
            for group in groups:
                if self.operator_group.lower() in group.lower():
                    return "operator"

        # No matching group found
        logger.warning(f"User not in any authorized LDAP group. Groups: {groups}")
        return None

    def is_enabled(self) -> bool:
        """Check if LDAP is enabled"""
        return self.enabled

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test LDAP connection

        Returns:
            Tuple of (success, message)
        """
        if not self.enabled:
            return False, "LDAP is disabled"

        try:
            conn = self._get_connection()
            if conn:
                conn.unbind()
                return True, "LDAP connection successful"
            else:
                return False, "Failed to connect to LDAP server"
        except Exception as e:
            return False, f"LDAP connection error: {str(e)}"


# Global LDAP service instance
ldap_service = LDAPService()
