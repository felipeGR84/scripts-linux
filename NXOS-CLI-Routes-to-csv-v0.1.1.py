import json
import csv
import os
from datetime import datetime
import re
from collections import defaultdict

def validate_file_path(prompt, expected_extension=None):
    while True:
        file_path = input(prompt)
        if expected_extension and not file_path.endswith(expected_extension):
            print(f"El archivo debe tener la extensión {expected_extension}.")
            continue
        if os.path.isfile(file_path):
            return file_path
        else:
            print("El archivo no existe. Por favor, inténtalo de nuevo.")

def validate_output_file_name(prompt):
    while True:
        file_name = input(prompt).strip()
        if file_name:
            return file_name
        else:
            print("El nombre del archivo no puede estar vacío. Por favor, inténtalo de nuevo.")

def parse_route_output():
    # Solicitar el archivo de rutas
    route_file_path = validate_file_path("Nombre del archivo con las RUTAS en txt (ejemplo: routes-output.txt): ", '.txt')
    
    with open(route_file_path, 'r') as file:
        output = file.read()
    routes = {}
    current_network = None
    
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # Match the network prefix and ubest/mbest info
        network_match = re.match(r"^(\d+\.\d+\.\d+\.\d+\/\d+),\s+ubest\/mbest:\s+(\d+)\/(\d+)", line)
        if network_match:
            current_network = network_match.group(1)
            ubest = int(network_match.group(2))
            mbest = int(network_match.group(3))
            
            routes[current_network] = {
                "ubest": ubest,
                "mbest": mbest,
                "paths": []
            }
        
        # Match the next hop information (via IP address, interface, etc.)
        path_match = re.match(
            r"^\*via\s+([\d\.]+),\s*([\w\/\.]+)?,?\s*\[(\d+)\/(\d+)\],?\s*((?:\d{2}:\d{2}:\d{2})|\d+\w+)?,?\s*(static|ospf-\d+|bgp)?(?:,\s*(intra|inter|type-1|type-2))?(?:,\s*tag\s*(\d+))?",
            line
        )
        if path_match and current_network:
            next_hop = path_match.group(1)
            interface = path_match.group(2) if path_match.group(2) else "N/A"
            ad = int(path_match.group(3)) if path_match.group(3) else "N/A"
            metric = int(path_match.group(4)) if path_match.group(4) else "N/A"
            age = path_match.group(5) if path_match.group(5) else "N/A"
            protocol = path_match.group(6) if path_match.group(6) else "N/A"
            route_type = path_match.group(7) if path_match.group(7) else "N/A"
            tag = path_match.group(8) if path_match.group(8) else "N/A"
            
            routes[current_network]["paths"].append({
                "next_hop": next_hop,
                "interface": interface,
                "administrative_distance": ad,
                "metric": metric,
                "age": age,
                "protocol": protocol,
                "route_type": route_type,
                "tag": tag
            })

    # Crear la carpeta con la fecha actual
    date_folder = datetime.now().strftime("%d-%m-%Y-rutas")
    if not os.path.exists(date_folder):
        os.makedirs(date_folder)

    # Guardar JSON temporalmente en la carpeta de fecha
    json_file_path = os.path.join(date_folder, "routes.json")
    with open(json_file_path, 'w') as json_file:
        json.dump(routes, json_file, indent=4)
    
    print(f"El archivo JSON de las rutas se ha guardado en {json_file_path}")

    # Solicitar el nombre del archivo CSV al usuario
    csv_file_name = validate_output_file_name("Ingrese el nombre con el que desea guardar el archivo CSV (sin extensión): ")
    csv_file_path = os.path.join(date_folder, f"{csv_file_name}.csv")

    # Guardar CSV en la carpeta de fecha con el nombre especificado
    with open(csv_file_path, 'w', newline='') as csv_file:
        fieldnames = ["network", "ubest", "next_hop", "interface", "administrative_distance", "metric", "age", "protocol", "route_type", "tag"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        # Escribir las rutas en el CSV
        for network, route_info in routes.items():
            for path in route_info["paths"]:
                writer.writerow({
                    "network": network,
                    "ubest": route_info["ubest"],
                    "next_hop": path["next_hop"],
                    "interface": path["interface"],
                    "administrative_distance": path["administrative_distance"],
                    "metric": path["metric"],
                    "age": path["age"],
                    "protocol": path["protocol"],
                    "route_type": path["route_type"],
                    "tag": path["tag"]
                })
    
    print(f"El archivo CSV de las rutas se ha guardado en {csv_file_path}")

    # Generar el reporte en un archivo .txt con el mismo nombre que el archivo CSV más el sufijo "-report"
    total_networks = len(routes)
    next_hop_counts = defaultdict(int)

    for route_info in routes.values():
        for path in route_info["paths"]:
            next_hop_counts[path["next_hop"]] += 1
    
    total_next_hops = len(next_hop_counts)

    # Crear el archivo de reporte en la misma carpeta
    report_file_name = f"{csv_file_name}-report.txt"
    report_file_path = os.path.join(date_folder, report_file_name)
    with open(report_file_path, 'w') as report_file:
        report_file.write(f"Total de redes: {total_networks}\n")
        report_file.write(f"Total de next-hops únicos: {total_next_hops}\n\n")
        report_file.write("Redes aprendidas por cada next-hop:\n")
        for next_hop, count in next_hop_counts.items():
            report_file.write(f"Next-hop {next_hop}: {count} redes\n")

    print(f"El archivo de reporte se ha guardado en {report_file_path}")

def main():
    parse_route_output()

if __name__ == "__main__":
    main()
