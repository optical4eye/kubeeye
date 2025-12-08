#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes cluster information management page
"""


# Import necessary libraries
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import re


# Page setup - must be the first Streamlit command
st.set_page_config(
    page_title="Cluster info - kubeeye",
    layout="wide"
)


# Add project root directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Import application modules
from utils.common import initialize_page
from utils.cluster_config import list_clusters, get_cluster, delete_cluster
from utils.node_connection import test_node_connection, validate_ssh_key
from utils.prometheus_client import PrometheusClient
from utils.k8s_client import K8sClient
from utils.node_parser import parse_nodes_from_text, generate_nodes_template


# Page initialization
initialize_page(
    title="Clusters",
    page_title="Cluster management",
    page_subtitle="Configure connections to Kubernetes clusters"
)


# Initialize session state for managing node list
if 'temp_nodes' not in st.session_state:
    st.session_state.temp_nodes = []


# Initialize state for hiding passwords
if 'show_passwords' not in st.session_state:
    st.session_state.show_passwords = {}

# Initialize state for validation
if 'validation_errors' not in st.session_state:
    st.session_state.validation_errors = {}


# Function for checking and validating keys
def validate_key_files(nodes):
    """
    Checks SSH keys for a list of nodes

    Args:
        nodes: list of nodes

    Returns:
        list of valid nodes, list of errors
    """
    valid_nodes = []
    key_errors = []

    for node_info in nodes:
        if node_info['auth_type'] == 'key':
            key_valid, key_message = validate_ssh_key(node_info['key_path'])
            if not key_valid:
                key_errors.append(f"Node {node_info['ip']}: {key_message}")
                continue
        valid_nodes.append(node_info)

    return valid_nodes, key_errors


def validate_ip_port(ip_port):
    """Validate IP:Port"""
    try:
        ip, port = ip_port.split(':')
        port = int(port)
        if port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535"
        # Simple IP check
        parts = ip.split('.')
        if len(parts) != 4:
            return False, "Invalid IP format"
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False, "Each IP part must be between 0 and 255"
        return True, ""
    except:
        return False, "Format must be IP:Port"


def validate_cluster_name(name):
    """Validate cluster name"""
    if not name:
        return False, "Cluster name is required"
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "Cluster name can only contain letters, numbers, hyphen and underscore"
    return True, ""


# Tabs for cluster management
tab1, tab2, tab3 = st.tabs(["Cluster list", "Add cluster", "Edit cluster"])

# Cluster list
with tab1:
    st.header("Configured clusters")

    if st.button("Refresh list"):
        st.rerun()

    clusters = list_clusters()

    if clusters:
        for cluster_name in clusters:
            with st.expander(f"Cluster: {cluster_name}", expanded=False):
                cluster_config = get_cluster(cluster_name)

                # Node information
                nodes = cluster_config.get_nodes()
                if nodes:
                    node_data = []
                    for node in nodes:
                        node_data.append({
                            "IP": node['ip'],
                            "Port": node['port'],
                            "User": node['username'],
                            "Authentication": node['auth_type']
                        })
                    st.dataframe(pd.DataFrame(node_data), use_container_width=True, hide_index=True)
                else:
                    st.info("Nodes not configured")

                # Prometheus configuration
                prometheus_config = cluster_config.get_prometheus_config()
                if prometheus_config.get('enabled'):
                    st.json(prometheus_config)

                # Kubeconfig
                kubeconfig = cluster_config.get_kubeconfig()
                if kubeconfig:
                    st.code(kubeconfig, language="yaml")
                else:
                    st.info("Kubeconfig not configured")

                # Cluster deletion
                if st.button("Delete cluster", key=f"delete_{cluster_name}"):
                    delete_cluster(cluster_name)
                    st.success(f"Cluster {cluster_name} deleted")
                    st.rerun()
    else:
        st.info("Clusters not configured")

# Add cluster
with tab2:
    st.header("Add new cluster")

    with st.form("add_cluster_form"):
        # Basic information
        cluster_name = st.text_input("Cluster name", placeholder="production", key="cluster_name_input")

        # Real-time cluster name validation
        if cluster_name:
            valid, error = validate_cluster_name(cluster_name)
            if not valid:
                st.error(f"{error}")
            else:
                st.success("Cluster name is correct")

        # Cluster nodes
        bulk_nodes_input = st.text_area(
            "Node list",
            placeholder="""Add SSH nodes for verification in the format: IP:User Identification Type Port [Password/Pathkey]
Examples:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa
10.0.1.50:2222 ubuntu password ubuntu123""",
height=200,
help="Each line must contain: IP:User Identification Type Port [Password/Pathkey]"
        )

        # Preliminary node check button
        check_nodes = st.form_submit_button("Check nodes")

        if check_nodes:
            if bulk_nodes_input:
                nodes, errors = parse_nodes_from_text(bulk_nodes_input)

                if errors:
                    for error in errors:
                        st.error(error)

                # Check keys before testing connection
                valid_nodes, key_errors = validate_key_files(nodes)

                if key_errors:
                    st.warning("SSH key issues detected:")
                    for error in key_errors:
                        st.error(error)

                    st.info("""
                    **Fix recommendations:**
                    - Ensure the key path is correct
                    - Check key format: `ssh-keygen -l -f /path/to/key`
                    - If necessary, convert key: `ssh-keygen -p -m PEM -f /path/to/key -N ""`
                    """)

                checked_count = 0
                success_count = 0

                for node_info in valid_nodes:
                    checked_count += 1
                    # Connection check
                    with st.spinner(f"Checking connection to {node_info['ip']}..."):
                        success, message = test_node_connection(node_info)

                    if success:
                        st.success(f"Node {node_info['ip']} is available")
                        success_count += 1
                    else:
                        st.error(f"Connection error with {node_info['ip']}: {message}")

                st.info(f"Check completed: {success_count}/{checked_count} nodes available")

                if key_errors:
                    st.warning(f"{len(key_errors)} nodes not checked due to key issues")
            else:
                st.warning("Enter node data for checking")

        # Prometheus configuration (collapsed by default)
        with st.expander("Prometheus configuration", expanded=False):
            st.caption("Configure Prometheus for monitoring")

            prometheus_enabled = st.checkbox("Enable Prometheus")

            col1, col2 = st.columns(2)
            with col1:
                prometheus_url = st.text_input("Prometheus URL", placeholder="http://prometheus.example.com:9090")
                prometheus_username = st.text_input("Username (optional)")

            with col2:
                prometheus_password = st.text_input("Password (optional)", type="password")
                prometheus_token = st.text_input("Token (optional)", type="password")

        # Kubeconfig
        st.subheader("Kubeconfig")

        # Initialize state for kubeconfig
        if 'kubeconfig_content' not in st.session_state:
            st.session_state.kubeconfig_content = ""

        # Field for manual kubeconfig input/editing
        kubeconfig_content = st.text_area(
            "Kubeconfig content",
            value=st.session_state.kubeconfig_content,
            height=150,
            placeholder="Paste kubeconfig content here...",
            help="Paste kubeconfig file content manually"
        )

        # Update state on manual editing
        if kubeconfig_content != st.session_state.kubeconfig_content:
            st.session_state.kubeconfig_content = kubeconfig_content

        # Persistent Kubernetes connection test button
        test_k8s = st.form_submit_button("Test Kubernetes connection")
        if test_k8s:
            if not st.session_state.kubeconfig_content:
                st.error("Enter kubeconfig content for connection test")
            else:
                with st.spinner("Testing Kubernetes connection..."):
                    k8s_client = K8sClient(st.session_state.kubeconfig_content)
                    success, message = k8s_client.test_connection()

                if success:
                    st.success("Kubernetes connection successful")
                else:
                    st.error(f"Kubernetes connection error: {message}")

        # Cluster save button
        submitted = st.form_submit_button("Save cluster")

        if submitted:
            if not cluster_name:
                st.error("Enter cluster name")
            elif not bulk_nodes_input:
                st.error("Add at least one node")
            else:
                # Parsing and validating nodes
                nodes, errors = parse_nodes_from_text(bulk_nodes_input)

                if errors:
                    for error in errors:
                        st.error(error)
                    st.error("Fix node format errors before saving")
                elif not nodes:
                    st.error("Failed to recognize any nodes")
                else:
                    # Check keys before testing connection
                    valid_nodes_for_check, key_errors = validate_key_files(nodes)

                    if key_errors:
                        st.warning("SSH key issues detected:")
                        for error in key_errors:
                            st.error(error)

                    # Connection check for all nodes
                    valid_nodes = []
                    failed_nodes = []

                    for node_info in valid_nodes_for_check:
                        with st.spinner(f"Checking connection to {node_info['ip']}..."):
                            success, message = test_node_connection(node_info)

                        if success:
                            valid_nodes.append(node_info)
                        else:
                            failed_nodes.append((node_info['ip'], message))

                    # Check Kubernetes connection (if kubeconfig provided)
                    k8s_connection_ok = True
                    k8s_error_message = ""

                    if st.session_state.kubeconfig_content:
                        with st.spinner("Testing Kubernetes connection..."):
                            k8s_client = K8sClient(st.session_state.kubeconfig_content)
                            k8s_success, k8s_message = k8s_client.test_connection()

                        if not k8s_success:
                            k8s_connection_ok = False
                            k8s_error_message = k8s_message

                    # Check Prometheus connection (if enabled)
                    prometheus_connection_ok = True
                    prometheus_error_message = ""

                    if prometheus_enabled and prometheus_url:
                        with st.spinner("Testing Prometheus connection..."):
                            prometheus_config = {
                                "url": prometheus_url,
                                "username": prometheus_username,
                                "password": prometheus_password,
                                "token": prometheus_token,
                                "enabled": True
                            }
                            prometheus_client = PrometheusClient(prometheus_config)
                            prometheus_result = prometheus_client.test_connection()

                        if prometheus_result.get('status') != 'success':
                            prometheus_connection_ok = False
                            prometheus_error_message = prometheus_result.get('error', 'Unknown error')

                    # Show check results
                    st.subheader("Check results:")

                    # Nodes
                    if failed_nodes:
                        st.error(f"Unavailable nodes ({len(failed_nodes)}):")
                        for ip, message in failed_nodes:
                            st.error(f"  - {ip}: {message}")
                    else:
                        st.success(f"All nodes available ({len(valid_nodes)})")

                    # Key issues
                    if key_errors:
                        st.error(f"Key issues ({len(key_errors)}):")
                        for error in key_errors:
                            st.error(f"  - {error}")

                    # Kubernetes
                    if st.session_state.kubeconfig_content:
                        if k8s_connection_ok:
                            st.success("Kubernetes connection successful")
                        else:
                            st.error(f"Kubernetes connection error: {k8s_error_message}")
                    else:
                        st.info("Kubeconfig not provided")

                    # Prometheus
                    if prometheus_enabled:
                        if prometheus_connection_ok:
                            st.success("Prometheus connection successful")
                        else:
                            st.error(f"Prometheus connection error: {prometheus_error_message}")
                    else:
                        st.info("Prometheus disabled")

                    # Save decision
                    if not valid_nodes:
                        st.error("No available nodes. Fix node configuration and try again.")
                    else:
                        # Ask for confirmation if there are issues
                        should_save = True
                        warning_message = ""

                        if failed_nodes:
                            warning_message += f"Only {len(valid_nodes)} out of {len(nodes)} nodes are available. "

                        if key_errors:
                            warning_message += f"{len(key_errors)} nodes have key issues. "

                        if st.session_state.kubeconfig_content and not k8s_connection_ok:
                            warning_message += "Kubernetes unavailable. "

                        if prometheus_enabled and not prometheus_connection_ok:
                            warning_message += "Prometheus unavailable. "

                        if warning_message:
                            st.warning(f"{warning_message}Are you sure you want to save the cluster?")
                            # In a real application, confirmation can be added here
                            # For simplicity, we continue saving but warn the user

                        # Creating new cluster
                        cluster_config = get_cluster(cluster_name)

                        # Adding available nodes
                        for node_info in valid_nodes:
                            cluster_config.update_node(node_info)

                        # Updating Prometheus configuration
                        prometheus_config = {
                            "url": prometheus_url,
                            "username": prometheus_username,
                            "password": prometheus_password,
                            "token": prometheus_token,
                            "enabled": prometheus_enabled
                        }
                        cluster_config.update_prometheus(prometheus_config)

                        # Updating kubeconfig
                        if st.session_state.kubeconfig_content:
                            cluster_config.update_kubeconfig(st.session_state.kubeconfig_content)

                        st.success(f"Cluster {cluster_name} added successfully")

                        # Clear kubeconfig after successful save
                        st.session_state.kubeconfig_content = ""

                        # Show summary
                        st.info(f"""
                        **Configuration summary:**
                        - Nodes: {len(valid_nodes)} available ({len(failed_nodes)} unavailable, {len(key_errors)} with key errors)
                        - Kubernetes: {'Available' if k8s_connection_ok else 'Unavailable'}
                        - Prometheus: {'Available' if prometheus_connection_ok else ('Unavailable' if prometheus_enabled else 'Disabled')}
                        """)


# Cluster editing
with tab3:
    st.header("Edit cluster")

    # Loading cluster list
    clusters = list_clusters()

    if not clusters:
        st.info("Clusters not configured yet, go to 'Add cluster' tab to create.")
    else:
        selected_cluster = st.selectbox("Select cluster to edit", clusters)

        if selected_cluster:
            cluster_config = get_cluster(selected_cluster)

            st.subheader(f"Edit cluster: {selected_cluster}")

            # Editing tabs
            edit_tab1, edit_tab2, edit_tab3 = st.tabs(["Node management", "Prometheus configuration", "Kubeconfig"])

            # Node management tab
            with edit_tab1:
                st.subheader("Node management")

                # Display existing nodes
                nodes = cluster_config.get_nodes()

                if nodes:
                    st.subheader("Current cluster nodes:")

                    # Create DataFrame for display with checkboxes
                    node_data = []
                    for node in nodes:
                        node_info = {
                            "Select for deletion": False,
                            "IP address": node['ip'],
                            "Port": node['port'],
                            "User": node['username'],
                            "Authentication type": node['auth_type'],
                            "Password/Key": node['password'] if node['auth_type'] == 'password' else node.get('key_path', node.get('password', ''))
                        }
                        node_data.append(node_info)

                    # Create interactive table with checkboxes
                    df = pd.DataFrame(node_data)

                    # Display table with row selection capability
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Select for deletion": st.column_config.CheckboxColumn(
                                "Select",
                                help="Select nodes for deletion",
                                default=False,
                            )
                        },
                        disabled=["IP address", "Port", "User", "Authentication type", "Password/Key"],
                        hide_index=True,
                        width='stretch'
                    )

                    # Process selected nodes for deletion
                    nodes_to_delete = []
                    for idx, row in edited_df.iterrows():
                        if row['Select for deletion']:
                            nodes_to_delete.append(row['IP address'])

                    # Button to delete selected nodes
                    if nodes_to_delete:
                        st.warning(f"Selected for deletion: {', '.join(nodes_to_delete)}")

                        if st.button("Delete selected nodes", type="secondary"):
                            for node_ip in nodes_to_delete:
                                cluster_config.remove_node(node_ip)
                            st.success(f"Deleted {len(nodes_to_delete)} nodes")
                            st.rerun()
                    else:
                        st.info("Select nodes for deletion by checking the 'Select for deletion' column")

                    # Bulk node actions
                    st.write("**Bulk node actions:**")

                    if st.button("Check all nodes", key="check_all_nodes"):
                        success_count = 0
                        for node in nodes:
                            # First check keys for nodes with key authentication
                            if node['auth_type'] == 'key':
                                key_path = node.get('key_path', node.get('password', ''))
                                key_valid, key_message = validate_ssh_key(key_path)
                                if not key_valid:
                                    st.error(f"Key error for {node['ip']}: {key_message}")
                                    continue

                            with st.spinner(f"Node check {node['ip']}..."):
                                success, message = test_node_connection(node)
                            if success:
                                st.success(f"Node {node['ip']} is available")
                                success_count += 1
                            else:
                                st.error(f"Node {node['ip']}: {message}")

                        st.info(f"Check completed: {success_count}/{len(nodes)} nodes available")

                else:
                    st.info("This cluster has no nodes.")

                # Section for adding new nodes
                st.subheader("Add new nodes")

                with st.form("add_nodes_form"):
                    new_nodes_input = st.text_area(
                        "New nodes to add",
                        placeholder="""Add SSH nodes for verification in the format: IP:User Identification Type Port [Password/Pathkey]
Examples:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa
10.0.1.50:2222 ubuntu password ubuntu123""",
                        height=150,
                        help="Each line must contain: IP:User Identification Type Port [Password/Pathkey]"
                    )


                    col1, col2 = st.columns(2)

                    with col1:
                        test_new_nodes = st.form_submit_button("Check new nodes")

                    with col2:
                        add_new_nodes = st.form_submit_button("Add new nodes")

                    if test_new_nodes:
                        if new_nodes_input:
                            new_nodes, errors = parse_nodes_from_text(new_nodes_input)

                            if errors:
                                for error in errors:
                                    st.error(error)

                            # Check keys before testing connection
                            valid_nodes, key_errors = validate_key_files(new_nodes)

                            if key_errors:
                                st.warning("SSH key issues detected:")
                                for error in key_errors:
                                    st.error(error)

                            checked_count = 0
                            success_count = 0

                            for node_info in valid_nodes:
                                checked_count += 1
                                with st.spinner(f"Connection check with {node_info['ip']}..."):
                                    success, message = test_node_connection(node_info)

                                if success:
                                    st.success(f"Node {node_info['ip']} is available")
                                    success_count += 1
                                else:
                                    st.error(f"Connection error with {node_info['ip']}: {message}")

                            st.info(f"Check completed: {success_count}/{checked_count} nodes available")

                            if key_errors:
                                st.warning(f"{len(key_errors)} nodes not checked due to key issues")
                        else:
                            st.warning("Enter node data for checking")

                    if add_new_nodes:
                        if new_nodes_input:
                            new_nodes, errors = parse_nodes_from_text(new_nodes_input)

                            if errors:
                                for error in errors:
                                    st.error(error)
                                st.error("Fix node format errors before adding")
                            elif not new_nodes:
                                st.error("Failed to recognize any nodes")
                            else:
                                # Check keys before adding
                                valid_nodes, key_errors = validate_key_files(new_nodes)

                                if key_errors:
                                    st.warning("SSH key issues detected:")
                                    for error in key_errors:
                                        st.error(error)

                                # Check connection and add only available nodes
                                added_count = 0
                                failed_count = 0

                                for node_info in valid_nodes:
                                    with st.spinner(f"Check and add node {node_info['ip']}..."):
                                        success, message = test_node_connection(node_info)

                                    if success:
                                        # Check if node with this IP already exists
                                        existing_nodes = cluster_config.get_nodes()
                                        node_exists = any(node['ip'] == node_info['ip'] for node in existing_nodes)

                                        if node_exists:
                                            st.warning(f"Node {node_info['ip']} already exists, updating configuration")

                                        cluster_config.update_node(node_info)
                                        added_count += 1
                                        st.success(f"Node {node_info['ip']} added")
                                    else:
                                        failed_count += 1
                                        st.error(f"Failed to add node {node_info['ip']}: {message}")

                                st.success(f"Added {added_count} new nodes")
                                if failed_count > 0:
                                    st.error(f"Failed to add {failed_count} nodes")

                                if key_errors:
                                    st.warning(f"{len(key_errors)} nodes not added due to key issues")

                                st.rerun()
                        else:
                            st.error("Enter node data to add")

            # Prometheus configuration tab
            with edit_tab2:
                st.subheader("Prometheus configuration")

                # Get current configuration
                prometheus_config = cluster_config.get_prometheus_config()

                with st.form("edit_prometheus_form"):
                    prometheus_enabled = st.checkbox("Enable Prometheus", value=prometheus_config.get('enabled', False))

                    col1, col2 = st.columns(2)
                    with col1:
                        prometheus_url = st.text_input("Prometheus URL", value=prometheus_config.get('url', ''))
                        prometheus_username = st.text_input("Username", value=prometheus_config.get('username', ''))

                    with col2:
                        prometheus_password = st.text_input("Password", type="password", value=prometheus_config.get('password', ''))
                        prometheus_token = st.text_input("Token", type="password", value=prometheus_config.get('token', ''))

                    # Connection test button
                    test_prom_button = st.form_submit_button("Test connection")

                    # Save configuration button
                    save_prom_button = st.form_submit_button("Save configuration")

                    if test_prom_button:
                        if not prometheus_url:
                            st.error("Enter Prometheus URL")
                        else:
                            # Forming temporary configuration
                            test_config = {
                                "url": prometheus_url,
                                "username": prometheus_username,
                                "password": prometheus_password,
                                "token": prometheus_token,
                                "enabled": True
                            }

                            # Connection test
                            with st.spinner("Connection test..."):
                                client = PrometheusClient(test_config)
                                result = client.test_connection()

                            if result.get('status') == 'success':
                                st.success("Connection successful")
                            else:
                                st.error(f"Connection error: {result.get('error', 'Unknown error')}")

                    if save_prom_button:
                        # Saving new configuration
                        new_config = {
                            "url": prometheus_url,
                            "username": prometheus_username,
                            "password": prometheus_password,
                            "token": prometheus_token,
                            "enabled": prometheus_enabled
                        }

                        cluster_config.update_prometheus(new_config)
                        st.success("Prometheus configuration updated")

            # Kubeconfig configuration tab
            with edit_tab3:
                st.subheader("Kubeconfig configuration")

                # Get current configuration
                current_kubeconfig = cluster_config.get_kubeconfig()

                # Initialize state for kubeconfig editing
                if 'edit_kubeconfig_content' not in st.session_state:
                    st.session_state.edit_kubeconfig_content = current_kubeconfig or ""

                with st.form("edit_kubeconfig_form"):
                    st.caption("Edit kubeconfig content manually")

                    # Field for editing kubeconfig
                    edit_kubeconfig_content = st.text_area(
                        "Kubeconfig content",
                        value=st.session_state.edit_kubeconfig_content,
                        height=300,
                        placeholder="Paste kubeconfig content here..."
                    )

                    # Update state when editing
                    if edit_kubeconfig_content != st.session_state.edit_kubeconfig_content:
                        st.session_state.edit_kubeconfig_content = edit_kubeconfig_content

                    # Persistent Kubernetes connection test button
                    test_kube_button = st.form_submit_button("Test Kubernetes connection")

                    # Save configuration button
                    save_kube_button = st.form_submit_button("Save configuration")

                    if test_kube_button:
                        if not st.session_state.edit_kubeconfig_content:
                            st.error("Enter kubeconfig content for connection test")
                        else:
                            # Connection test
                            with st.spinner("Connection test..."):
                                client = K8sClient(st.session_state.edit_kubeconfig_content)
                                success, message = client.test_connection()

                            if success:
                                st.success("Kubernetes connection successful")
                            else:
                                st.error(f"Connection error: {message}")

                    if save_kube_button:
                        # Update configuration
                        cluster_config.update_kubeconfig(st.session_state.edit_kubeconfig_content)
                        st.success("Kubeconfig configuration updated")
