import json
import csv
import os
from datetime import datetime
from genie.conf.base import Device
from genie.libs.parser.nxos import show_arp as nxos_show_arp, show_fdb as nxos_show_mac
from genie.libs.parser.iosxe import show_arp as iosxe_show_arp, show_fdb as iosxe_show_mac

# Function to validate file path
def validate_file_path(file_path):
    if os.path.isfile(file_path) and (file_path.endswith('.txt') or file_path.endswith('.log')):
        return file_path
    else:
        return None

# Function to parse ARP output with pyATS
def parse_arp_output(device, output, os_type):
    try:
        if os_type == 'nxos':
            return nxos_show_arp.ShowIpArp(device=device).cli(output=output)
        elif os_type == 'iosxe':
            return iosxe_show_arp.ShowIpArp(device=device).cli(output=output)
    except Exception as e:
        print(f"Error al analizar el archivo ARP: {e}")
        return None

# Function to parse MAC table output with pyATS
def parse_mac_output(device, output, os_type):
    try:
        if os_type == 'nxos':
            return nxos_show_mac.ShowMacAddressTable(device=device).cli(output=output)
        elif os_type == 'iosxe':
            return iosxe_show_mac.ShowMacAddressTable(device=device).cli(output=output)
    except Exception as e:
        print(f"Error al analizar el archivo MAC: {e}")
        return None

# Function to validate available interfaces and check for omitted ones
def validate_existing_interfaces(available_interfaces):
    print(f"Interfaces disponibles: {', '.join(available_interfaces)}")
    while True:
        omitted_interfaces = input("Ingrese las interfaces a omitir, separadas por comas o presione Enter para omitir: ").split(',')
        omitted_interfaces = [interface.strip() for interface in omitted_interfaces if interface.strip()]
        non_existent = [interface for interface in omitted_interfaces if interface not in available_interfaces]
        
        if non_existent:
            print(f"Las siguientes interfaces no existen: {', '.join(non_existent)}.")
        else:
            return omitted_interfaces

# Function to match MAC and ARP data
def match_mac_arp(arp_data, mac_data, mac_file_label):
    # Get available interfaces from MAC data
    available_interfaces = {entry['interface'] for vlan in mac_data['mac_table']['vlans'].values()
                            for mac in vlan['mac_addresses'].values()
                            for entry in mac.get('interfaces', {}).values()}

    print(f"Available interfaces in MAC data (Label: {mac_file_label}): {available_interfaces}")
    
    omitted_interfaces = validate_existing_interfaces(available_interfaces)

    matches = []
    total_mac_count = 0
    matched_mac_count = 0

    # Iterate over ARP data (ARP IP-to-MAC entries)
    for arp_interface, arp_intf_data in arp_data['interfaces'].items():
        for arp_ip, arp_entry in arp_intf_data['ipv4']['neighbors'].items():
            arp_mac = arp_entry["link_layer_address"]  # MAC address from ARP table
            arp_interface = arp_entry["physical_interface"]  # Interface from ARP table (e.g., Vlan491)

            print(f"Processing ARP entry: IP={arp_ip}, MAC={arp_mac}, Interface={arp_interface}")

            # Now, let's check for the MAC address in the MAC address table
            for vlan_data in mac_data['mac_table']['vlans'].values():
                mac_entry = vlan_data['mac_addresses'].get(arp_mac)
                if mac_entry:
                    total_mac_count += 1
                    # Iterate through the interfaces to find a match for the interface from the MAC table
                    for mac_interface, mac_details in mac_entry.get('interfaces', {}).items():
                        mac_vlan = vlan_data['vlan']

                        print(f"Found MAC {arp_mac} in VLAN {mac_vlan} with Interface {mac_interface}")

                        # Check if the MAC address is in the same VLAN (VLAN comparison logic)
                        if arp_interface.startswith("Vlan"):  # ARP entry interface is VLAN
                            arp_vlan = arp_interface  # VLAN from ARP entry
                            print(f"Comparing ARP interface {arp_interface} (VLAN: {arp_vlan}) with MAC interface {mac_interface} (VLAN: {mac_vlan})")
                            if arp_vlan == f"Vlan{mac_vlan}":  # Ensure the VLANs match (fix comparison here)
                                # If the interface is not omitted, we have a valid match
                                if mac_interface not in omitted_interfaces:
                                    matches.append({
                                        "IP": arp_ip,
                                        "MAC": arp_mac,
                                        "VLAN": mac_vlan,
                                        "Interface": mac_interface,
                                        "MAC File Label": mac_file_label  # Add MAC file label to match
                                    })
                                    matched_mac_count += 1
                                    print(f"Match found for IP: {arp_ip}, MAC: {arp_mac}, VLAN: {mac_vlan}, Interface: {mac_interface}")
                        elif arp_interface.startswith("Port-channel"):  # ARP entry interface is Port-channel
                            # Handle Port-channel interface matching separately
                            if mac_interface.startswith("Port-channel"):
                                if mac_interface == arp_interface:  # Match if Port-channel interfaces match
                                    if mac_interface not in omitted_interfaces:
                                        matches.append({
                                            "IP": arp_ip,
                                            "MAC": arp_mac,
                                            "VLAN": mac_vlan,
                                            "Interface": mac_interface,
                                            "MAC File Label": mac_file_label  # Add MAC file label to match
                                        })
                                        matched_mac_count += 1
                                        print(f"Match found for IP: {arp_ip}, MAC: {arp_mac}, VLAN: {mac_vlan}, Interface: {mac_interface}")

    # Debugging: Show final counts
    print(f"Total MACs in MAC table: {total_mac_count}, Matched MACs: {matched_mac_count}")

    return matches, total_mac_count, matched_mac_count

# Function to save results in CSV and TXT
def save_results(matches, mac_file_labels, total_mac_count, matched_mac_count):
    current_date = datetime.now().strftime("%d-%m-%Y")
    folder_name = f"{current_date}-match"
    os.makedirs(folder_name, exist_ok=True)

    output_csv_file = input("Ingrese el nombre del archivo CSV (sin extensión): ") + '.csv'
    output_csv_path = os.path.join(folder_name, output_csv_file)
    output_txt_path = os.path.join(folder_name, "match_summary.txt")

    # Create a new CSV or append if the file exists
    file_exists = os.path.isfile(output_csv_path)

    # Save CSV file (append mode if file exists)
    with open(output_csv_path, 'a', newline='') as csv_file:
        fieldnames = ["IP","MAC", "VLAN", "Interface", "MAC File Label"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        # Write the header only if the file does not exist
        if not file_exists:
            writer.writeheader()

        for match in matches:
            writer.writerow(match)

    # Save summary to TXT file
    with open(output_txt_path, 'w') as txt_file:
        txt_file.write(f"Resumen de coincidencias - {current_date}\n")
        txt_file.write("=" * 50 + "\n")
        txt_file.write(f"Total de direcciones MAC en todos los archivos: {total_mac_count}\n")
        txt_file.write(f"Total de coincidencias en todos los archivos: {matched_mac_count}\n\n")

        # Separate summary by MAC file label
        for label in mac_file_labels:
            file_matches = [m for m in matches if m['MAC File Label'] == label]
            file_mac_count = len(file_matches)
            file_matched_count = sum(1 for m in file_matches if m['MAC'] in [m['MAC'] for m in matches])

            txt_file.write(f"Resumen del archivo MAC con etiqueta: {label}\n")
            txt_file.write(f"Total de MACs en archivo: {file_mac_count}\n")
            txt_file.write(f"Total de coincidencias en archivo: {file_matched_count}\n\n")
            for match in file_matches:
                txt_file.write(f"IP: {match['IP']},MAC: {match['MAC']}, VLAN: {match['VLAN']}, Interface: {match['Interface']}\n")

    print(f"Resultados guardados en {output_csv_path} y {output_txt_path}")

# Main function
def main():
    print("Bienvenido al programa de coincidencias de MAC y ARP con pyATS.")

    # Ask for ARP file path
    while True:
        arp_file_path = input("Nombre del archivo con la salida de ARP en .txt o .log: ").strip()
        if validate_file_path(arp_file_path):
            break
        else:
            print("El archivo ARP no es válido. Por favor, inténtalo de nuevo.")

    with open(arp_file_path, 'r') as arp_file:
        arp_output = arp_file.read()

    # Set up device and load outputs
    device = Device(name='virtual_device', os='nxos')  # Adjust based on your device
    arp_data = parse_arp_output(device, arp_output, os_type='nxos')  # Change 'os_type' as needed

    if not arp_data:
        print("Error al analizar el archivo ARP.")
        return

    # Prompt for multiple MAC files
    mac_files = []
    mac_file_labels = []
    while True:
        mac_file_path = input("Nombre del archivo con la salida de MAC en .txt o .log (o escribe 'fin' para terminar): ").strip()
        if mac_file_path.lower() == 'fin':
            break

        while True:
            mac_file_label = input(f"Nombre o etiqueta para este archivo de MAC (se usará en CSV): ").strip()
            if mac_file_label:
                break
            else:
                print("La etiqueta no puede estar vacía. Por favor, ingresa un nombre o etiqueta.")

        # Validate the MAC file
        if validate_file_path(mac_file_path):
            mac_files.append(mac_file_path)
            mac_file_labels.append(mac_file_label)
        else:
            print("El archivo no existe o no tiene extensión válida (.txt o .log). Por favor, inténtalo de nuevo.")

    # Ensure at least one MAC file is available
    if not mac_files:
        print("No se proporcionaron archivos MAC válidos. El programa finalizará.")
        return

    # Parse MAC data
    all_matches = []
    total_mac_count = 0
    matched_mac_count = 0

    for mac_file_path, mac_file_label in zip(mac_files, mac_file_labels):
        with open(mac_file_path, 'r') as mac_file:
            mac_output = mac_file.read()

        mac_data = parse_mac_output(device, mac_output, os_type='nxos')  # Change 'os_type' based on device
        if not mac_data:
            print(f"Error al analizar el archivo MAC: {mac_file_label}.")
            continue

        matches, file_mac_count, file_matched_count = match_mac_arp(arp_data, mac_data, mac_file_label)

        # Append the matches for this file
        all_matches.extend(matches)
        total_mac_count += file_mac_count
        matched_mac_count += file_matched_count

    # Save the results to CSV and TXT
    save_results(all_matches, mac_file_labels, total_mac_count, matched_mac_count)

# Run the main function
if __name__ == '__main__':
    main()
