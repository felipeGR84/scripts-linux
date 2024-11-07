import json
import csv
import re
import os
from datetime import datetime

def validate_file_path(prompt, expected_extension=None):
    while True:
        file_path = input(prompt)
        if expected_extension and not file_path.endswith(expected_extension):
            print(f"El archivo debe tener la extensión {expected_extension}.")
        elif os.path.isfile(file_path):
            return file_path
        else:
            print("El archivo no existe. Por favor, inténtalo de nuevo.")

# Función para leer el archivo de salida de MAC y generar el JSON temporal
def read_mac_output():
    mac_file_path = validate_file_path("Nombre del archivo con las tabla MACs en txt (ejemplo: macs-output.txt): ", '.txt')
    with open(mac_file_path, 'r') as file:
        output = file.read()

    pattern = re.compile(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)')
    mac_data = [
        {
            "Indicator": match.group(1),
            "VLAN": match.group(2),
            "MAC": match.group(3),
            "Type": match.group(4),
            "Age": match.group(5),
            "Flag1": match.group(6),
            "Flag2": match.group(7),
            "Interface": match.group(8),
        }
        for line in output.strip().splitlines() if (match := pattern.match(line))
    ]

    json_path = os.path.splitext(mac_file_path)[0] + '.json'
    with open(json_path, 'w') as json_file:
        json.dump(mac_data, json_file, indent=4)

    print(f"La salida de MACs se ha guardado temporalmente en {json_path}")
    return json_path

# Función para leer el archivo de salida de ARP y generar el JSON temporal
def read_arp_output():
    arp_file_path = validate_file_path("Nombre del archivo con la tabla ARP en txt (ejemplo: arp-output.txt): ", '.txt')
    with open(arp_file_path, 'r') as file:
        output = file.read()

    pattern = re.compile(r'(\S+)\s+(\S+)\s+(\S+)\s+Vlan(\d+)\s*\*?')
    arp_data = [
        {
            "IP": match.group(1),
            "Time": match.group(2),
            "MAC": match.group(3),
            "VLAN": match.group(4),
        }
        for line in output.strip().splitlines() if (match := pattern.match(line))
    ]

    json_path = os.path.splitext(arp_file_path)[0] + '.json'
    with open(json_path, 'w') as json_file:
        json.dump(arp_data, json_file, indent=4)

    print(f"La salida de ARP se ha guardado temporalmente en {json_path}")
    return json_path

# Función para crear la carpeta con la fecha actual y guardar el archivo CSV
def save_csv_in_dated_folder(matches, hostname):
    # Obtener la fecha actual en el formato D-M-Y
    current_date = datetime.now().strftime("%d-%m-%Y")
    folder_name = f"{current_date}-match"
    
    # Crear la carpeta si no existe
    os.makedirs(folder_name, exist_ok=True)
    
    # Solicitar nombre del archivo CSV
    output_csv_file = input("Ingrese el nombre con el que se guarda los match (sin extensión, ejemplo: match-acceso-21): ") + '.csv'
    output_csv_path = os.path.join(folder_name, output_csv_file)
    
    # Guardar el archivo CSV
    with open(output_csv_path, 'w', newline='') as csv_file:
        fieldnames = list(matches[0].keys()) + ['Hostname']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for entry in matches:
            entry['Hostname'] = hostname
            writer.writerow(entry)
    
    print(f"El archivo se ha guardado en {output_csv_path}")

# Función para hacer match entre los datos de MAC y ARP
def match_mac_arp(mac_json_path, arp_json_path):
    with open(mac_json_path, 'r') as json_file:
        mac_data = json.load(json_file)

    with open(arp_json_path, 'r') as json_file:
        arp_data = json.load(json_file)

    # Filtrar interfaces si es necesario
    available_interfaces = {entry["Interface"] for entry in mac_data}
    omitted_interfaces = input("Ingrese las interfaces a omitir, separadas por comas. Ejemplo: vPC,Po11 (o presione Enter para omitir): ").split(',')
    omitted_interfaces = [interface.strip() for interface in omitted_interfaces if interface.strip()]

    # Hacer match y agregar coincidencias
    matches = [
        {
            "IP": arp_entry["IP"],
            "MAC": arp_entry["MAC"],
            "VLAN": arp_entry["VLAN"],
            "Interface": mac_entry["Interface"],
        }
        for arp_entry in arp_data
        for mac_entry in mac_data
        if arp_entry["MAC"] == mac_entry["MAC"] and arp_entry["VLAN"] == mac_entry["VLAN"] and mac_entry["Interface"] not in omitted_interfaces
    ]

    # Mostrar estadísticas
    print(f"Total de direcciones MAC: {len(mac_data)}")
    print(f"Total de coincidencias: {len(matches)}")

    # Guardar los resultados en CSV en la carpeta con la fecha actual
    hostname = input("Ingrese el hostname del equipo: ")
    save_csv_in_dated_folder(matches, hostname)

# Función principal
def main():
    mac_json_path = read_mac_output()
    arp_json_path = read_arp_output()
    match_mac_arp(mac_json_path, arp_json_path)

if __name__ == "__main__":
    main()
