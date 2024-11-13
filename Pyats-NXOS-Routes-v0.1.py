import json
import csv
import os
from collections import defaultdict
from datetime import datetime
from genie.conf.base import Device
from genie.libs.parser.nxos import show_routing

# Function to validate file path, supporting both .txt and .log extensions
def validate_file_path(prompt, expected_extensions=None):
    while True:
        file_path = input(prompt)
        if file_path.lower() == 'end':
            print("Cerrando el programa.")
            exit()
        if expected_extensions and not any(file_path.endswith(ext) for ext in expected_extensions):
            print(f"El archivo debe tener una de las siguientes extensiones: {', '.join(expected_extensions)}.")
            continue
        if os.path.isfile(file_path):
            return file_path
        else:
            print("El archivo no existe. Por favor, inténtalo de nuevo.")

# Function to validate and ensure output file has .csv extension
def validate_output_file_name(prompt):
    while True:
        file_name = input(prompt).strip()
        if file_name.lower() == 'end':
            print("Cerrando el programa.")
            exit()
        if file_name:
            if not file_name.endswith('.csv'):
                file_name += '.csv'
            return file_name
        else:
            print("El nombre del archivo no puede estar vacío. Por favor, inténtalo de nuevo.")

# Function to create a folder named with the current date
def create_date_folder():
    date_folder = datetime.now().strftime("%d-%m-%Y-routes")
    try:
        os.makedirs(date_folder, exist_ok=True)
        print(f"Directory created: {date_folder}")
    except Exception as e:
        print(f"Error creating directory {date_folder}: {e}")
    return date_folder

# Function to parse the 'show_ip_route_output' into JSON
def parse_show_ip_route(show_ip_route_output, date_folder):
    device = Device(name='virtual_device', os='iosxe')
    device.custom.setdefault('abstraction', {'order': ['os']})

    try:
        parsed_output = show_routing.ShowIpRoute(device=device).cli(output=show_ip_route_output)
        
        # Save parsed output as a JSON file
        with open(os.path.join(date_folder, 'parsed_output.json'), 'w') as json_file:
            json.dump(parsed_output, json_file, indent=4)
        
        print(f"Parsed JSON saved to parsed_output.json in {date_folder}")
        return parsed_output
    except Exception as e:
        print("Error parsing show_ip_route output:", e)
        return None

# Function to convert JSON data to CSV
def convert_json_to_csv(parsed_data, csv_file_path):
    try:
        with open(csv_file_path, mode='w', newline='') as csv_file:
            fieldnames = ["vrf", "protocol", "network", "distance", "metric", "next_hop", "time", "interface", "source_protocol_status", "tag"]
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()

            for vrf, vrf_data in parsed_data["vrf"].items():
                for route, route_info in vrf_data["address_family"]["ipv4"]["routes"].items():
                    protocol = route_info.get("source_protocol", "n/a").upper()
                    network = route_info.get("route", "n/a")
                    distance = route_info.get("route_preference", "n/a")
                    metric = route_info.get("metric", "n/a")
                    #source_protocol_codes = route_info.get("source_protocol_codes", "n/a")
                    source_protocol_status = route_info.get("source_protocol_status", "n/a") if protocol == "OSPF" else "n/a"
                    tag = route_info.get("tag", "n/a") if protocol == "OSPF" else "n/a"

                    next_hop_info = route_info.get("next_hop", {}).get("next_hop_list", {})
                    for hop_index, hop_details in next_hop_info.items():
                        csv_writer.writerow({
                            "vrf": vrf,
                            "protocol": protocol,
                            "network": network,
                            "distance": distance,
                            "metric": metric,
                            "next_hop": hop_details.get("next_hop", "n/a"),
                            "time": hop_details.get("updated", "n/a"),
                            "interface": hop_details.get("outgoing_interface", "n/a"),
                            #"source_protocol_codes": source_protocol_codes,
                            "source_protocol_status": hop_details.get("source_protocol_status", "n/a") if protocol == "OSPF" else "n/a",
                            "tag": tag
                        })

        print(f"CSV file created at: {csv_file_path}")
    except Exception as e:
        print(f"Error converting JSON to CSV: {e}")

# Function to generate a report based on CSV data, organized by VRF
def generate_report(csv_file_path, date_folder):
    routes = defaultdict(lambda: defaultdict(list))
    next_hop_counts = defaultdict(lambda: defaultdict(int))

    try:
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                vrf = row.get("vrf", "default")
                network = row.get("network")
                next_hop = row.get("next_hop")

                if network and next_hop:
                    routes[vrf][next_hop].append(network)
                    next_hop_counts[vrf][next_hop] += 1

        report_file_name = f"{os.path.splitext(csv_file_path)[0]}-report.txt"
        report_file_path = report_file_name

        with open(report_file_path, 'w') as report_file:
            for vrf, vrf_next_hops in routes.items():
                total_networks = sum(len(nh_networks) for nh_networks in vrf_next_hops.values())
                total_next_hops = len(vrf_next_hops)

                report_file.write(f"\nVRF: {vrf}\n")
                report_file.write(f"Total de redes: {total_networks}\n")
                report_file.write(f"Total de next-hops únicos: {total_next_hops}\n\n")
                report_file.write("Redes aprendidas por cada next-hop:\n")

                for next_hop, networks in vrf_next_hops.items():
                    count = next_hop_counts[vrf][next_hop]
                    report_file.write(f"  Next-hop {next_hop}: {count} redes\n")

        print(f"El archivo de reporte se ha guardado en {report_file_path}")
    except Exception as e:
        print(f"Error generating report: {e}")

# Main function
def main():
    # Step 1: Get the input file path and output CSV file name
    show_ip_route_file_path = validate_file_path(
        "Introduce el archivo de salida de show ip route (por ejemplo, show_ip_route_output.txt or. log, si quiere cerrar el programa introduce 'end'): ",
        [".txt", ".log"]
    )
    csv_file_name = validate_output_file_name("Introduce el nombre del archivo CSV de salida (por ejemplo, output.csv): ")

    # Step 2: Create date-based folder
    date_folder = create_date_folder()
    csv_file_path = os.path.join(date_folder, csv_file_name)

    # Step 3: Read the content from the show_ip_route file
    with open(show_ip_route_file_path, 'r') as file:
        show_ip_route_output = file.read()

    # Step 4: Parse the show_ip_route_output using genie
    parsed_data = parse_show_ip_route(show_ip_route_output, date_folder)

    if parsed_data:
        # Step 5: Convert the parsed data to CSV
        convert_json_to_csv(parsed_data, csv_file_path)
        
        # Step 6: Generate the report
        generate_report(csv_file_path, date_folder)

# Run the main function
if __name__ == "__main__":
    main()
