import json
import csv
import os
import re
from datetime import datetime

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

def txt_to_json(txt_file_path):
    with open(txt_file_path, 'r') as file:
        output = file.read()
    
    routes = {}
    current_network = None
    
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # Coincidencia para prefijos de red y ubest/mbest
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
        
        # Coincidencia para información de next-hop
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
    
    # Guardar archivo JSON con el mismo nombre que el archivo de texto
    json_file_path = txt_file_path.replace(".txt", ".json")
    with open(json_file_path, 'w') as json_file:
        json.dump(routes, json_file, indent=4)
    
    return json_file_path

def compare_next_hop(json1, json2):
    differences = []
    all_networks = set(json1.keys()).union(set(json2.keys()))
    
    for network in all_networks:
        if network in json1 and network in json2:
            paths1 = json1[network]["paths"]
            paths2 = json2[network]["paths"]
            
            # Comprobar si el next-hop cambió
            for path1 in paths1:
                next_hop_before = path1["next_hop"]
                matching_path = next((p for p in paths2 if p["next_hop"] == next_hop_before), None)
                
                if not matching_path:
                    next_hop_after = paths2[0]["next_hop"] if paths2 else "N/A"
                    differences.append((network, next_hop_before, next_hop_after))
    
    return differences

def save_differences_to_csv(differences, csv_file_path):
    with open(csv_file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Network", "Next-hop Antes", "Next-hop Después"])
        for diff in differences:
            writer.writerow(diff)
    
    print(f"El archivo CSV con el resumen de diferencias en next-hop se ha guardado en {csv_file_path}")

def main():
    txt_file1 = validate_file_path("Ingrese la tabla de rutas del antes en txt: ", ".txt")
    txt_file2 = validate_file_path("Ingrese la tabla de rutas del despues en txt: ", ".txt")
    
    json_file1 = txt_to_json(txt_file1)
    json_file2 = txt_to_json(txt_file2)
    
    with open(json_file1, 'r') as f1:
        data1 = json.load(f1)
    with open(json_file2, 'r') as f2:
        data2 = json.load(f2)
    
    differences = compare_next_hop(data1, data2)
    
    date_folder = datetime.now().strftime("%d-%m-%Y-diff")
    if not os.path.exists(date_folder):
        os.makedirs(date_folder)
    
    csv_file_name = input("Ingrese el nombre para generar el archivo CSV con las rutas que cambiaron de next-hop (sin extensión): ").strip()
    csv_file_path = os.path.join(date_folder, f"{csv_file_name}.csv")
    
    save_differences_to_csv(differences, csv_file_path)

if __name__ == "__main__":
    main()
