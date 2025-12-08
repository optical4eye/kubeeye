#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes certificate checking module for checking cluster certificate expiration status
"""

import yaml
import base64
import logging
import tempfile
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

def get_cluster_cert_status(cluster_name: str, kubeconfig_content: str) -> Dict[str, any]:
    """
    Check cluster certificate status

    Args:
        cluster_name: cluster name
        kubeconfig_content: kubeconfig file content

    Returns:
        Dict: dictionary containing certificate status information
        {
            'status': 'valid|warning|critical|expired|unknown',
            'days_remaining': int,  # remaining days, negative numbers mean expired
            'cert_info': {
                'issuer': str,
                'subject': str,
                'not_before': str,
                'not_after': str
            },
            'error': str  # if there is an error
        }
    """
    try:
        if not kubeconfig_content:
            return {
                'status': 'unknown',
                'days_remaining': None,
                'error': 'kubeconfig content is empty'
            }

        # Parse kubeconfig
        kubeconfig = yaml.safe_load(kubeconfig_content)
        if not kubeconfig:
            return {
                'status': 'unknown',
                'days_remaining': None,
                'error': 'unable to parse kubeconfig content'
            }

        # Check client certificate
        cert_info = _extract_client_cert_info(kubeconfig)
        if not cert_info:
            # If no client certificate, check cluster CA certificate
            cert_info = _extract_cluster_ca_info(kubeconfig)

        if not cert_info:
            return {
                'status': 'unknown',
                'days_remaining': None,
                'error': 'no valid certificate information found'
            }

        # Calculate certificate status
        return _calculate_cert_status(cert_info)

    except Exception as e:
        logger.error(f"Error occurred while checking certificate status for cluster {cluster_name}: {str(e)}")
        return {
            'status': 'unknown',
            'days_remaining': None,
            'error': f'error occurred while checking certificate: {str(e)}'
        }


def _extract_client_cert_info(kubeconfig: Dict) -> Optional[Dict]:
    """Extract client certificate information from kubeconfig"""
    try:
        users = kubeconfig.get('users', [])
        for user in users:
            user_info = user.get('user', {})

            # Check client-certificate-data
            cert_data = user_info.get('client-certificate-data')
            if cert_data:
                cert_bytes = base64.b64decode(cert_data)
                return _parse_certificate(cert_bytes)

            # Check client-certificate file path
            cert_path = user_info.get('client-certificate')
            if cert_path and Path(cert_path).exists():
                with open(cert_path, 'rb') as f:
                    cert_bytes = f.read()
                return _parse_certificate(cert_bytes)

        return None

    except Exception as e:
        logger.error(f"Failed to extract client certificate information: {str(e)}")
        return None


def _extract_cluster_ca_info(kubeconfig: Dict) -> Optional[Dict]:
    """Extract cluster CA certificate information from kubeconfig"""
    try:
        clusters = kubeconfig.get('clusters', [])
        for cluster in clusters:
            cluster_info = cluster.get('cluster', {})

            # Check certificate-authority-data
            ca_data = cluster_info.get('certificate-authority-data')
            if ca_data:
                cert_bytes = base64.b64decode(ca_data)
                return _parse_certificate(cert_bytes)

            # Check certificate-authority file path
            ca_path = cluster_info.get('certificate-authority')
            if ca_path and Path(ca_path).exists():
                with open(ca_path, 'rb') as f:
                    cert_bytes = f.read()
                return _parse_certificate(cert_bytes)

        return None

    except Exception as e:
        logger.error(f"Failed to extract cluster CA certificate information: {str(e)}")
        return None


def _parse_certificate(cert_bytes: bytes) -> Optional[Dict]:
    """Parse certificate and extract information"""
    try:
        # Try to parse certificate in PEM format
        cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())

        return {
            'issuer': cert.issuer.rfc4514_string(),
            'subject': cert.subject.rfc4514_string(),
            'not_before': cert.not_valid_before_utc,
            'not_after': cert.not_valid_after_utc,
            'serial_number': str(cert.serial_number)
        }

    except Exception as e:
        logger.error(f"Failed to parse certificate: {str(e)}")
        return None


def _calculate_cert_status(cert_info: Dict) -> Dict[str, any]:
    """Calculate status based on certificate information"""
    try:
        not_after = cert_info['not_after']
        not_before = cert_info['not_before']
        now = datetime.now(timezone.utc)

        # Ensure time objects have timezone information
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        if not_before.tzinfo is None:
            not_before = not_before.replace(tzinfo=timezone.utc)

        # Calculate remaining days
        time_remaining = not_after - now
        days_remaining = time_remaining.days

        # Determine status
        if now > not_after:
            status = 'expired'
        elif days_remaining <= 7:  # expires within 7 days
            status = 'critical'
        elif days_remaining <= 30:  # expires within 30 days
            status = 'warning'
        else:
            status = 'valid'

        return {
            'status': status,
            'days_remaining': days_remaining,
            'cert_info': {
                'issuer': cert_info['issuer'],
                'subject': cert_info['subject'],
                'not_before': not_before.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'not_after': not_after.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'serial_number': cert_info.get('serial_number', '')
            }
        }

    except Exception as e:
        logger.error(f"Failed to calculate certificate status: {str(e)}")
        return {
            'status': 'unknown',
            'days_remaining': None,
            'error': f'failed to calculate certificate status: {str(e)}'
        }


def check_certificate_file(cert_path: str) -> Dict[str, any]:
    """
    Check status of individual certificate file

    Args:
        cert_path: path to certificate file

    Returns:
        Dict: certificate status information
    """
    try:
        if not Path(cert_path).exists():
            return {
                'status': 'unknown',
                'days_remaining': None,
                'error': f'certificate file does not exist: {cert_path}'
            }

        with open(cert_path, 'rb') as f:
            cert_bytes = f.read()

        cert_info = _parse_certificate(cert_bytes)
        if not cert_info:
            return {
                'status': 'unknown',
                'days_remaining': None,
                'error': f'unable to parse certificate file: {cert_path}'
            }

        return _calculate_cert_status(cert_info)

    except Exception as e:
        logger.error(f"Failed to check certificate file {cert_path}: {str(e)}")
        return {
            'status': 'unknown',
            'days_remaining': None,
            'error': f'failed to check certificate file: {str(e)}'
        }


def get_certificate_details(kubeconfig_content: str) -> Dict[str, any]:
    """
    Get detailed information about all certificates in kubeconfig

    Args:
        kubeconfig_content: kubeconfig file content

    Returns:
        Dict: dictionary containing detailed information about all certificates
    """
    try:
        kubeconfig = yaml.safe_load(kubeconfig_content)
        if not kubeconfig:
            return {'error': 'unable to parse kubeconfig content'}

        details = {
            'client_certificates': [],
            'cluster_ca_certificates': [],
            'summary': {
                'total_certs': 0,
                'expired_certs': 0,
                'expiring_soon_certs': 0,
                'earliest_expiry': None
            }
        }

        # Check client certificates
        users = kubeconfig.get('users', [])
        for user in users:
            user_name = user.get('name', 'unknown')
            user_info = user.get('user', {})

            cert_data = user_info.get('client-certificate-data')
            cert_path = user_info.get('client-certificate')

            if cert_data:
                cert_bytes = base64.b64decode(cert_data)
                cert_info = _parse_certificate(cert_bytes)
                if cert_info:
                    status = _calculate_cert_status(cert_info)
                    details['client_certificates'].append({
                        'user': user_name,
                        'type': 'client-certificate-data',
                        **status
                    })
            elif cert_path:
                status = check_certificate_file(cert_path)
                details['client_certificates'].append({
                    'user': user_name,
                    'type': 'client-certificate-file',
                    'path': cert_path,
                    **status
                })

        # Check cluster CA certificates
        clusters = kubeconfig.get('clusters', [])
        for cluster in clusters:
            cluster_name = cluster.get('name', 'unknown')
            cluster_info = cluster.get('cluster', {})

            ca_data = cluster_info.get('certificate-authority-data')
            ca_path = cluster_info.get('certificate-authority')

            if ca_data:
                cert_bytes = base64.b64decode(ca_data)
                cert_info = _parse_certificate(cert_bytes)
                if cert_info:
                    status = _calculate_cert_status(cert_info)
                    details['cluster_ca_certificates'].append({
                        'cluster': cluster_name,
                        'type': 'certificate-authority-data',
                        **status
                    })
            elif ca_path:
                status = check_certificate_file(ca_path)
                details['cluster_ca_certificates'].append({
                    'cluster': cluster_name,
                    'type': 'certificate-authority-file',
                    'path': ca_path,
                    **status
                })

        # Calculate summary information
        all_certs = details['client_certificates'] + details['cluster_ca_certificates']
        details['summary']['total_certs'] = len(all_certs)

        earliest_expiry = None
        for cert in all_certs:
            if cert.get('status') == 'expired':
                details['summary']['expired_certs'] += 1
            elif cert.get('status') in ['critical', 'warning']:
                details['summary']['expiring_soon_certs'] += 1

            days_remaining = cert.get('days_remaining')
            if days_remaining is not None:
                if earliest_expiry is None or days_remaining < earliest_expiry:
                    earliest_expiry = days_remaining

        details['summary']['earliest_expiry'] = earliest_expiry

        return details

    except Exception as e:
        logger.error(f"Failed to get detailed certificate information: {str(e)}")
        return {'error': f'failed to get detailed certificate information: {str(e)}'}
