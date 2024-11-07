import heapq
import csv
import json

# Función para cargar el grafo desde un archivo JSON
def cargar_grafo_desde_json(filename):
    with open(filename, 'r') as file:
        graph = json.load(file)
    # Convertir cada peso a `float` para permitir valores decimales
    return {k: [(dest, float(peso)) for dest, peso in v] for k, v in graph.items()}


# Función Dijkstra para encontrar los k mejores caminos de un nodo a otro
def dijkstra_k_shortest_paths(graph, start, target, k=5, max_hops=10):
    # Min-heap para almacenar (costo, nodo_actual, camino_recorrido, brincos, nodos_visitados)
    queue = [(0, start, [start], 0, set([start]))]
    best_paths = []
    
    while queue and len(best_paths) < k:
        cost, current_node, path, hops, visited = heapq.heappop(queue)

        # Si llegamos al nodo destino, añadimos el camino a los mejores caminos
        if current_node == target:
            best_paths.append((path, cost, hops))
            continue

        # Limitar la longitud del camino (brincos) para reducir el uso de memoria
        if hops >= max_hops:
            continue

        # Explorar vecinos
        for neighbor, weight in graph.get(current_node, []):
            new_cost = cost + weight
            # Continuar solo si el vecino no ha sido visitado en el camino actual
            if neighbor in visited:
                continue
            
            # Crear un nuevo conjunto de nodos visitados incluyendo el vecino actual
            new_visited = visited | {neighbor}
            heapq.heappush(queue, (new_cost, neighbor, path + [neighbor], hops + 1, new_visited))

    return best_paths

# Función para guardar los resultados en formato CSV
def save_paths_to_csv(paths, filename='mejores_caminos.csv'):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Escribir encabezados
        writer.writerow(['Camino', 'Costo Total', 'Brincos'])
        
        # Escribir datos de los caminos
        for i, (path, cost, hops) in enumerate(paths, 1):
            path_str = ' → '.join(path)
            writer.writerow([f"Camino {i}: {path_str}", cost, hops])
    
    print(f"\nResultados guardados en el archivo {filename}")

# Cargar el grafo desde el archivo JSON
filename = 'graph-to-be-2024.json'
graph = cargar_grafo_desde_json(filename)

# Solicitar al usuario el nodo de origen y destino
start_node = input("Ingresa el nodo de origen: ")
target_node = input("Ingresa el nodo de destino: ")

# Obtener los 5 mejores caminos desde el origen hasta el destino
k = 10
best_paths = dijkstra_k_shortest_paths(graph, start_node, target_node, k)

# Mostrar los mejores caminos
if best_paths:
    print(f"\nLos {k} mejores caminos de {start_node} a {target_node} son:\n")
    for i, (path, cost, hops) in enumerate(best_paths, 1):
        print(f"Camino {i}: {' → '.join(path)}")
        print(f"  Costo total: {cost}")
        print(f"  Número de brincos (hops): {hops}\n")
    
    # Guardar resultados en formato CSV
    save_paths_to_csv(best_paths)

else:
    print(f"\nNo se encontraron caminos de {start_node} a {target_node}.")
