import json
import csv
import os
from collections import defaultdict
from datetime import datetime
from genie.conf.base import Device
from genie.libs.parser.iosxe import show_routing

# Function to validate file path
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

# Function to validate and ensure output file has .csv extension
def validate_output_file_name(prompt):
    while True:
        file_name = input(prompt).strip()
        if file_name:
            # Ensure the file name ends with .csv
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
            fieldnames = ["vrf", "protocol", "network", "distance", "metric", "next_hop", "time", "interface", "source_protocol_codes"]
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()

            # Iterate over the VRFs and routes, and extract relevant data
            for vrf_name, vrf_data in parsed_data.get("vrf", {}).items():
                for af, af_data in vrf_data.get("address_family", {}).items():
                    for network, route_info in af_data.get("routes", {}).items():
                        protocol = route_info.get("source_protocol", "n/a").upper()
                        network = route_info.get("route", "n/a")
                        distance = route_info.get("route_preference", "n/a")
                        metric = route_info.get("metric", "n/a")
                        source_protocol_codes = route_info.get("source_protocol_codes", "n/a")

                        # Extract next hop information
                        next_hop_info = route_info.get("next_hop", {}).get("next_hop_list", {})
                        for hop_index, hop_details in next_hop_info.items():
                            csv_writer.writerow({
                                "vrf": vrf_name,
                                "protocol": protocol,
                                "network": network,
                                "distance": distance,
                                "metric": metric,
                                "next_hop": hop_details.get("next_hop", "n/a"),
                                "time": hop_details.get("updated", "n/a"),
                                "interface": hop_details.get("outgoing_interface", "n/a"),
                                "source_protocol_codes": source_protocol_codes
                            })

        print(f"CSV file created at: {csv_file_path}")
    except Exception as e:
        print(f"Error converting JSON to CSV: {e}")

# Function to generate a report based on CSV data
# Function to generate a report based on CSV data, organized by VRF
def generate_report(csv_file_path, date_folder):
    routes = defaultdict(lambda: defaultdict(list))  # Nested dictionary to store VRF -> next-hop -> networks
    next_hop_counts = defaultdict(lambda: defaultdict(int))  # Nested dictionary for VRF -> next-hop -> count

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

        # Generate the report text
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
                    #for network in networks:
                     #   report_file.write(f"    - {network}\n")

        print(f"El archivo de reporte se ha guardado en {report_file_path}")
    except Exception as e:
        print(f"Error generating report: {e}")


# Main function
def main():
    # Step 1: Get the input file path and output CSV file name
    show_ip_route_file_path = validate_file_path("Introduce el archivo de salida de show ip route (por ejemplo, show_ip_route_output.txt): ", ".txt")
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
