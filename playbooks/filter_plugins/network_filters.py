#!/usr/bin/python3
# -*- coding: utf-8 -*-

class FilterModule(object):
    def filters(self):
        return {
            'expand_bond_interfaces': self.expand_bond_interfaces
        }

    def expand_bond_interfaces(self, networks):
        """
        Expand bond interfaces into individual network interfaces for each port.
        
        Args:
            networks: List of network interface configurations
            
        Returns:
            List of expanded network interfaces
        """
        expanded_networks = []
        
        for network in networks:
            if isinstance(network, dict) and network.get('type') == 'bond':
                # For bond interfaces, create individual interfaces for each port
                bond_name = network.get('name', 'bond0')
                bond_network = network.get('network', 'VM Network')
                ports = network.get('link-aggregation', {}).get('port', [])
                
                for i, port in enumerate(ports):
                    expanded_networks.append({
                        'name': port,  # Use the port name (e.g., ens192, ens224)
                        'network': bond_network,
                        'type': 'vmxnet3',
                        'dhcp': network.get('dhcp', False)
                    })
            else:
                # For regular interfaces, keep as is
                expanded_networks.append(network)
        
        return expanded_networks 