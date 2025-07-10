#!/usr/bin/python3

import ipaddress

def merge_dicts(base, override):
    """Merge recursivo de diccionarios preservando la estructura base."""
    if not isinstance(override, dict):
        return override
    
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

def merge_interfaces(base_interfaces, override_interfaces):
    """Merge de listas de interfaces por nombre."""
    if not override_interfaces:
        return base_interfaces
    
    result = base_interfaces.copy()
    override_names = {interface['name'] for interface in override_interfaces}
    
    # Actualizar interfaces existentes
    for i, base_interface in enumerate(result):
        if base_interface['name'] in override_names:
            for override_interface in override_interfaces:
                if override_interface['name'] == base_interface['name']:
                    result[i] = merge_dicts(base_interface, override_interface)
                    break
    
    # Agregar interfaces nuevas
    existing_names = {interface['name'] for interface in result}
    for override_interface in override_interfaces:
        if override_interface['name'] not in existing_names:
            result.append(override_interface)
    
    return result

def build_network_config(node_data, machine_network, node_overrides=None):
    """Construir la estructura networkConfig para un nodo."""
    if node_overrides is None:
        node_overrides = {}
    
    # Inicializar networkConfig
    network_config = {
        'interfaces': [],
        'dns-resolver': {'config': {'server': []}},
        'routes': {'config': []}
    }
    
    # Procesar interfaces Ethernet
    networks = node_data.get('networks', {})
    bond_ports = set()
    
    # Identificar puertos de bond basándose en bond_interfaces
    bond_interfaces = node_data.get('bond_interfaces', [])
    for bond in bond_interfaces:
        if 'link-aggregation' in bond and 'port' in bond['link-aggregation']:
            for port in bond['link-aggregation']['port']:
                bond_ports.add(port)
    
    # Crear configuraciones de interfaces
    for interface_name, network in networks.items():
        is_bond_port = interface_name in bond_ports
        
        interface_config = {
            'name': interface_name,
            'type': 'ethernet',
            'state': 'up',
            'mac-address': network['mac'],
            'ipv4': {
                'enabled': 'false' if is_bond_port else 'true',
                'dhcp': 'false'
            },
            'ipv6': {
                'enabled': 'false'
            }
        }
        
        # Configurar IP para la interfaz principal (ens192) si hay IP disponible en node_data
        if not is_bond_port and interface_name == 'ens192' and node_data.get('ip'):
            interface_config['ipv4']['address'] = [{
                'ip': node_data['ip'],
                'prefix-length': node_data.get('prefix_length', 24)
            }]
        elif not is_bond_port and 'ip' in network:
            # Para otras interfaces que tengan IP específica
            interface_config['ipv4']['address'] = [{
                'ip': network['ip'],
                'prefix-length': network.get('prefix_length', 24)
            }]
        elif network.get('dhcp') or node_data.get('use_dhcp'):
            interface_config['ipv4']['dhcp'] = 'true'
        
        network_config['interfaces'].append(interface_config)
    
    # Procesar interfaces Bond
    for i, bond in enumerate(bond_interfaces):
        bond_config = {
            'name': bond['name'],
            'type': 'bond',
            'state': 'up',
            'link-aggregation': {
                'mode': bond['link-aggregation']['mode'],
                'options': {
                    'miimon': bond['link-aggregation']['options']['miimon']
                },
                'port': bond['link-aggregation']['port']
            },
            'ipv4': {
                'enabled': 'true' if i == 0 else 'false',
                'dhcp': 'false'
            },
            'ipv6': {
                'enabled': 'false'
            }
        }
        
        # Configurar IP para el primer bond
        if i == 0 and node_data.get('ip'):
            bond_config['ipv4']['address'] = [{
                'ip': node_data['ip'],
                'prefix-length': node_data.get('prefix_length', 24)
            }]
        elif node_data.get('use_dhcp'):
            bond_config['ipv4']['dhcp'] = 'true'
        
        network_config['interfaces'].append(bond_config)
    
    # Configurar DNS (nameserver o dns-resolver format)
    if not node_data.get('use_dhcp') or 'dns-resolver' in node_overrides:
        if 'dns-resolver' in machine_network:
            network_config['dns-resolver'] = merge_dicts(
                network_config['dns-resolver'], 
                machine_network['dns-resolver']
            )
        elif 'nameserver' in machine_network:
            # Manejar el caso simple donde nameserver es una string
            nameserver = machine_network['nameserver']
            if isinstance(nameserver, str):
                network_config['dns-resolver']['config']['server'] = [nameserver]
            elif isinstance(nameserver, list):
                network_config['dns-resolver']['config']['server'] = nameserver
    else:
        network_config.pop('dns-resolver', None)
    
    # Configurar rutas
    gateway = machine_network.get('gateway', {})
    gateway_address = gateway.get('address') if isinstance(gateway, dict) else gateway
    
    # Determinar la interfaz del gateway dinámicamente
    gateway_interface = None
    
    # Verificar si hay una interfaz bond0 en las interfaces del nodo
    has_bond0 = any(bond['name'] == 'bond0' for bond in bond_interfaces)
    
    # Lógica de priorización para la interfaz del gateway:
    # 1. Si está definida networkconfig.gateway.interface o overrides.gateway.interface -> lo que se indique
    # 2. Si hay bond0 y ens192 es parte de él -> bond0
    # 3. En cualquier otro caso, ens192
    if isinstance(gateway, dict) and gateway.get('interface'):
        gateway_interface = gateway.get('interface')
    elif has_bond0 and 'ens192' in bond_ports:
        gateway_interface = 'bond0'
    else:
        gateway_interface = 'ens192'
    
    # Crear ruta por defecto si no hay DHCP o si hay overrides de gateway
    should_create_routes = not node_data.get('use_dhcp') or 'gateway' in node_overrides
    if should_create_routes and gateway_address and gateway_interface:
        network_config['routes']['config'].append({
            'destination': '0.0.0.0/0',
            'next-hop-address': gateway_address,
            'next-hop-interface': gateway_interface
        })
    
    # Si no hay rutas configuradas, eliminar la sección routes
    if not network_config['routes']['config']:
        network_config.pop('routes', None)

    # Aplicar overrides del nodo
    if node_overrides:
        if 'interfaces' in node_overrides:
            network_config['interfaces'] = merge_interfaces(
                network_config['interfaces'], 
                node_overrides['interfaces']
            )
        
        if 'dns-resolver' in node_overrides:
            if 'dns-resolver' in network_config:
                network_config['dns-resolver'] = merge_dicts(
                    network_config['dns-resolver'], 
                    node_overrides['dns-resolver']
                )
            else:
                network_config['dns-resolver'] = node_overrides['dns-resolver']
        elif 'nameserver' in node_overrides:
            # Manejar el caso simple donde nameserver es una string en overrides
            nameserver = node_overrides['nameserver']
            if isinstance(nameserver, str):
                network_config['dns-resolver']['config']['server'] = [nameserver]
            elif isinstance(nameserver, list):
                network_config['dns-resolver']['config']['server'] = nameserver
        
        if 'gateway' in node_overrides:
            if 'routes' in network_config and network_config['routes']['config']:
                override_gateway = node_overrides['gateway']
                # Manejar tanto string como objeto
                if isinstance(override_gateway, str):
                    # Caso simple: gateway es una string
                    override_address = override_gateway
                    override_interface = gateway_interface
                else:
                    # Caso complejo: gateway es un objeto
                    override_address = override_gateway.get('address', gateway_address)
                    override_interface = override_gateway.get('interface', gateway_interface)
                
                network_config['routes']['config'][0].update({
                    'next-hop-address': override_address,
                    'next-hop-interface': override_interface
                })
    # Si hay override de gateway y no existe ninguna ruta, crearla con el override
    if 'gateway' in node_overrides and ('routes' not in network_config or not network_config['routes'].get('config')):
        override_gateway = node_overrides['gateway']
        network_config.setdefault('routes', {'config': []})
        # Manejar tanto string como objeto
        if isinstance(override_gateway, str):
            # Caso simple: gateway es una string
            override_address = override_gateway
            override_interface = gateway_interface
        else:
            # Caso complejo: gateway es un objeto
            override_address = override_gateway.get('address')
            override_interface = override_gateway.get('interface', gateway_interface)
        
        if override_address and override_interface:
            network_config['routes']['config'].append({
                'destination': '0.0.0.0/0',
                'next-hop-address': override_address,
                'next-hop-interface': override_interface
            })
        if not network_config['routes']['config']:
            network_config.pop('routes', None)

    return network_config

import os
import json
import sys

def main():
    # Leer variables de entorno
    node_data = json.loads(os.environ.get('NODE_DATA', '{}'))
    machine_network = json.loads(os.environ.get('MACHINE_NETWORK', '{}'))
    node_overrides = json.loads(os.environ.get('NODE_OVERRIDES', '{}'))
    
    try:
        result = build_network_config(node_data, machine_network, node_overrides)
        print(json.dumps(result))
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 