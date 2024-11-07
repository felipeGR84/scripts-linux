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

# Función para validar si el archivo contiene información extraíble y del tipo correcto
def validate_file_content(file_path, pattern, file_type):
    with open(file_path, 'r') as file:
        content = file.read()
        if not pattern.search(content):
            print(f"El archivo '{file_path}' no contiene información válida para un archivo de {file_type}.")
            return False
    return True

# Función para leer el archivo de salida de MAC y generar el JSON temporal
def read_mac_output():
    mac_file_path = validate_file_path("Nombre del archivo con las direcciones MACs en txt (ejemplo: macs-output.txt): ", '.txt')
    
    mac_pattern = re.compile(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)')
    while True:
        if validate_file_content(mac_file_path, mac_pattern, "MAC"):
            break
        mac_file_path = validate_file_path("Por favor, proporciona un archivo válido de direcciones MACs en txt: ", '.txt')

    with open(mac_file_path, 'r') as file:
        output = file.read()

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
        for line in output.strip().splitlines() if (match := mac_pattern.match(line))
    ]

    if not mac_data:
        print(f"No se encontraron datos válidos en el archivo '{mac_file_path}'. Asegúrate de que el formato sea correcto.")
        return None

    json_path = os.path.splitext(mac_file_path)[0] + '.json'
    with open(json_path, 'w') as json_file:
        json.dump(mac_data, json_file, indent=4)

    print(f"La salida de MACs se ha guardado temporalmente en {json_path}")
    return json_path

# Función para leer el archivo de salida de ARP y generar el JSON temporal
def read_arp_output():
    arp_file_path = validate_file_path("Nombre del archivo con la tabla ARP en txt (ejemplo: arp-output.txt): ", '.txt')
    
    arp_pattern = re.compile(r'(\S+)\s+(\S+)\s+(\S+)\s+Vlan(\d+)\s*\*?')
    while True:
        if validate_file_content(arp_file_path, arp_pattern, "ARP"):
            break
        arp_file_path = validate_file_path("Por favor, proporciona un archivo válido de tabla ARP en txt: ", '.txt')

    with open(arp_file_path, 'r') as file:
        output = file.read()

    arp_data = [
        {
            "IP": match.group(1),
            "Time": match.group(2),
            "MAC": match.group(3),
            "VLAN": match.group(4),
        }
        for line in output.strip().splitlines() if (match := arp_pattern.match(line))
    ]

    if not arp_data:
        print(f"No se encontraron datos válidos en el archivo '{arp_file_path}'. Asegúrate de que el formato sea correcto.")
        return None

    json_path = os.path.splitext(arp_file_path)[0] + '.json'
    with open(json_path, 'w') as json_file:
        json.dump(arp_data, json_file, indent=4)

    print(f"La salida de ARP se ha guardado temporalmente en {json_path}")
    return json_path

# Función para validar que las interfaces a omitir existan
def validate_existing_interfaces(available_interfaces):
    #print(f"Interfaces disponibles: {', '.join(available_interfaces)}")
    while True:
        omitted_interfaces = input("Ingrese las interfaces a omitir, separadas por comas (Ejemplo: Po1,Eth3/19) o presione Enter para omitir este paso: ").split(',')
        omitted_interfaces = [interface.strip() for interface in omitted_interfaces if interface.strip()]
        non_existent = [interface for interface in omitted_interfaces if interface not in available_interfaces]
        
        if non_existent:
            print(f"Las siguientes interfaces no existen: {', '.join(non_existent)}. Por favor, verifica y vuelve a intentarlo.")
        else:
            return omitted_interfaces

# Función para crear la carpeta con la fecha actual y guardar el archivo CSV
def save_csv_in_dated_folder(matches, hostname):
    current_date = datetime.now().strftime("%d-%m-%Y")
    folder_name = f"{current_date}-match"
    
    os.makedirs(folder_name, exist_ok=True)
    output_csv_file = input("Ingrese el nombre del archivo CSV (sin extensión, ejemplo: match): ") + '.csv'
    output_csv_path = os.path.join(folder_name, output_csv_file)

    # Comprobar si el archivo CSV ya existe
    file_exists = os.path.isfile(output_csv_path)
    
    with open(output_csv_path, 'a', newline='') as csv_file:  # Abrir en modo 'append'
        fieldnames = list(matches[0].keys()) + ['Hostname']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        # Si el archivo no existe, escribir la cabecera
        if not file_exists:
            writer.writeheader()
        
        for entry in matches:
            entry['Hostname'] = hostname
            writer.writerow(entry)
    
    print(f"Los resultados se han guardado en {output_csv_path}")

# Función para hacer match entre los datos de MAC y ARP
def match_mac_arp(mac_json_path, arp_json_path):
    with open(mac_json_path, 'r') as json_file:
        mac_data = json.load(json_file)

    with open(arp_json_path, 'r') as json_file:
        arp_data = json.load(json_file)

    available_interfaces = {entry["Interface"] for entry in mac_data if entry["Interface"]}
    omitted_interfaces = validate_existing_interfaces(available_interfaces)

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

    print(f"Total de direcciones MAC: {len(mac_data)}")
    print(f"Total de coincidencias: {len(matches)}")

    hostname = input("Ingrese el hostname del equipo: ")
    save_csv_in_dated_folder(matches, hostname)

    # Preguntar si el usuario desea continuar
    while True:
        continuar = input("¿Desea realizar otro análisis de coincidencias? (s/n): ").strip().lower()
        if continuar in ('s', 'n'):
            break
        print("Por favor, ingrese 's' para sí o 'n' para no.")

    if continuar == 's':
        print("Reiniciando el proceso...")
        main()
    else:
        print("Saliendo del programa.")

# Función principal con introducción
def main():
    print("Bienvenido al programa de procesamiento de datos de MAC y ARP.")
    print("Este programa realiza las siguientes funciones:")
    print("1. Lee un archivo con direcciones MAC y lo convierte en un archivo JSON temporal.")
    print("2. Lee un archivo con una tabla ARP y lo convierte en un archivo JSON temporal.")
    print("3. Compara las direcciones MAC con la tabla ARP para encontrar coincidencias.")
    print("4. Guarda las coincidencias en un archivo CSV en una carpeta con la fecha actual.")
    print("\nPor favor, sigue las instrucciones para seleccionar los archivos y proporcionar los datos necesarios.\n")
    
    while True:  # Bucle para asegurarse de que el archivo de MAC sea válido
        mac_json_path = read_mac_output()
        if mac_json_path:  # Verificar que se obtuvo una ruta válida
            break

    while True:  # Bucle para asegurarse de que el archivo de ARP sea válido
        arp_json_path = read_arp_output()
        if arp_json_path:  # Verificar que se obtuvo una ruta válida
            break
    
    match_mac_arp(mac_json_path, arp_json_path)

if __name__ == "__main__":
    main()
