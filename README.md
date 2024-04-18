# Deploy OCP4 using ABI in vSphere
I've been engaged lastly in different Red Hat OpenShift 4 deployments using 
Agent Based Installer (ABI) deployments in vSphere and created this set of 
playbooks to make some tasks easier.

Requirements:
- vCenter connection data
- vCenter user with enough permissions
- DNS for API/Ingress
- OpenShift Installer in the $PATH

Usage:
- Create inventory file for each cluster
- Create and encrypt the vault file using the template
- Run the all-in-one playbook:
```
$ ansible-playbook -i inventories/sno.yaml -e @inventories/vault.yaml --ask-vault-password playbooks/create-cluster.yaml
```

TODO:
- Add the cluster version in the inventory and download the installer
- Add requirements.txt for Ansible dependencies

