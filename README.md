# OCP4 ABI vSphere Ansible Playbooks

Ansible playbooks for automated OpenShift 4 deployment using Agent-Based Installer (ABI) in vSphere environments.

## Overview

This project provides playbooks to automate the complete lifecycle of OpenShift 4 clusters using ABI in vSphere:
- Cluster creation and deployment
- VM management and configuration
- Network setup and IP allocation
- ISO image generation and upload
- Snapshot management
- Cluster destruction

## Playbooks

### Main Playbooks
These are the main playbooks that will be used most of the time:
- `create-cluster.yaml` - Complete cluster deployment (imports all other playbooks)
- `destroy-cluster.yaml` - Remove cluster and all associated VMs
- `snapshot-cluster.yaml` - Manage VM snapshots (create/remove/revert)

### Supporting Playbooks
These are some extra playbooks, used by the main playbooks, but that have some individual value also:
- `create-abi-files.yaml` - Generate installation configuration files
- `create-abi-image.yaml` - Create and upload ISO image to vSphere datastore
- `create-vms.yaml` - Create and configure virtual machines
- `upload-abi-image.yaml` - Upload existing ISO to datastore
- `wait-for-install-complete.yaml` - Monitor installation progress

## Features

- **Flexible Topologies**: Support for SNO (Single Node OpenShift), HA clusters, and custom configurations
- **Network Configuration**: Static IP and DHCP support with bond interface configuration
- **Multi-NIC Support**: Multiple network interfaces per node with individual configuration
- **Node-Level Overrides**: Custom network interface configuration per node
- **Custom Manifests**: Include additional Kubernetes manifests during installation
- **vSphere Integration**: Full integration with vCenter for VM lifecycle management
- **Snapshot Management**: Create, remove, and revert VM snapshots
- **Multi-Datastore**: Support for multiple vSphere datastores

## Requirements

- vCenter access with appropriate permissions
- OpenShift installer in PATH
- DNS configured for API/Ingress endpoints
- Ansible with VMware collection

## Installation

```bash
pip install -r requirements.txt
ansible-galaxy collection install -r collections/requirements.yml
```

## Usage

1. Create inventory file based on provided examples
2. Optionally, create encrypted vault file with sensitive data like vCenter credentials
3. Run deployment:

```bash
ansible-playbook -i inventories/your-inventory.yaml -e @inventories/vault.yaml --ask-vault-password playbooks/create-cluster.yaml
```

## Inventory Structure

Inventory files define:
- Cluster name and domain
- Control plane and compute node counts
- Network configuration (CIDR, gateway, DNS)
- VM specifications (CPU, memory, disk, networks)
- vCenter datastore configuration
- vCenter cluster selection (can be overridden per VM)

VM resources can be defined at three levels, with higher priority overriding lower:
1. `vms.defaultConfig`
2. `vms.controlPlaneConfig` / `vms.computeConfig`
3. `templateOverrides.vms.nodeXX`

A few examples have been created in the See the  [`inventories/`](inventories/) directory.

## Network Configuration

Network configuration allows:
- to attach many virtual interfaces to the nodes 
- to configure, using a known format, the network interfaces configuration at the operating system level

### Multi-NIC Support
Nodes can have multiple network interfaces with different configurations:
```yaml
networks:
- name: ens192
  network: VM Routed Network
- name: ens224
  network: VM Isolated Network
```

Note: to include extra network interfaces at the node level use `additional_networks` instead. See the  [`inventories/ocp4-multinic.yaml`](inventories/ocp4-multinic.yaml) example file.

### Node-Level Overrides
Custom network configuration per node using `templateOverrides`:
```yaml
templateOverrides:
  vms:
    node00:
      cluster: zone2
      interfaces:
      - name: ens224
        ipv4:
          address: 10.11.1.103
          prefix-length: 24
```

You can also use the full FQDN for backward compatibility, but `nodeXX` is preferred.

### Bond Interfaces
Support for network bonding with multiple ports:
```yaml
networks:
- name: bond0
  type: bond
  network: VM Network
  link-aggregation:
    port: [ens192, ens224]
```

See the  [`inventories/ocp4-sno-bond.yaml`](inventories/ocp4-sno-bond.yaml) example file.

## Custom Manifests

Include additional Kubernetes manifests during installation by placing them in `inventories/extra_manifests/` and referencing them in the inventory:

```yaml
extra_manifests:
- openshift-sdn.yaml
- custom-operator.yaml
```

Manifests are copied to the installation directory and included in the generated ISO.

## Example Configurations

A few examples have been created in the See the  [`inventories/`](inventories/) directory:

- **SNO**: Single control plane node
- **HA**: Multiple control plane nodes with compute nodes
- **Multi-NIC**: Multiple network interfaces per node
- **Bond Interfaces**: Network bonding configurations
- **Static/DHCP**: IP address allocation methods
- **Node Overrides**: Custom per-node configurations


## TODO

There are a few things yet to be done for future updates:
- Include version parameter in the cluster definition
- Include openshift-install binary download if not present
- Include a custom CA to the installation
- Allow referencing a file for the SSH key instead of a variable

Feel free to collaborate! ❤️


