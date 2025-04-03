from typing import List, Tuple, Dict
import numpy as np
from models.distribution_center import DistributionCenter
from models.factory import Factory
import pandas as pd

class RouteOptimizer:
    """Otimiza as rotas de entrega usando o algoritmo de Clarke-Wright Savings."""
    
    def __init__(self, factory: Factory, distribution_center: DistributionCenter, points_of_sale: pd.DataFrame):
        """
        Inicializa o otimizador de rotas.
        
        Args:
            factory: Fábrica de origem
            distribution_center: Centro de distribuição
            points_of_sale: DataFrame com os pontos de venda a serem atendidos
        """
        self.factory = factory
        self.distribution_center = distribution_center
        self.points_of_sale = points_of_sale
        self.current_route = None  # Rota atual para cálculo de custos
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula a distância em km entre dois pontos usando a fórmula de Haversine."""
        R = 6371  # Raio da Terra em km
        
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c
    
    def build_distance_matrix(self) -> np.ndarray:
        """Constrói a matriz de distâncias entre todos os pontos."""
        n = len(self.points_of_sale)
        distances = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                pdv_i = self.points_of_sale.iloc[i]
                pdv_j = self.points_of_sale.iloc[j]
                dist = self.calculate_distance(
                    pdv_i['latitude'], pdv_i['longitude'],
                    pdv_j['latitude'], pdv_j['longitude']
                )
                distances[i,j] = distances[j,i] = dist
        
        return distances
    
    def build_savings_matrix(self, distances: np.ndarray) -> np.ndarray:
        """Constrói a matriz de economias do algoritmo Clarke-Wright."""
        n = len(self.points_of_sale)
        savings = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                pdv_i = self.points_of_sale.iloc[i]
                pdv_j = self.points_of_sale.iloc[j]
                
                # Distância do CD ao ponto i
                dist_cd_i = self.calculate_distance(
                    self.distribution_center.latitude, self.distribution_center.longitude,
                    pdv_i['latitude'], pdv_i['longitude']
                )
                
                # Distância do CD ao ponto j
                dist_cd_j = self.calculate_distance(
                    self.distribution_center.latitude, self.distribution_center.longitude,
                    pdv_j['latitude'], pdv_j['longitude']
                )
                
                # Economia = dist(CD,i) + dist(CD,j) - dist(i,j)
                savings[i,j] = savings[j,i] = dist_cd_i + dist_cd_j - distances[i,j]
        
        return savings
    
    def optimize_routes(self, vehicle_capacity: float, max_stops_per_day: float) -> List[List[int]]:
        """
        Otimiza as rotas usando uma abordagem de clusterização e vizinho mais próximo.
        
        Args:
            vehicle_capacity: Capacidade do veículo em kg
            max_stops_per_day: Número máximo de paradas por dia
        
        Returns:
            Lista de rotas, onde cada rota é uma lista de índices dos pontos de venda
        """
        n = len(self.points_of_sale)
        if n == 0:
            return []
        
        # Lista de pontos ainda não atendidos
        unvisited = list(range(n))
        routes = []
        
        while unvisited:
            # Encontra o ponto mais distante do CD para começar uma nova rota
            max_distance = 0
            start_point = None
            
            for point_idx in unvisited:
                point = self.points_of_sale.iloc[point_idx]
                distance = self.calculate_distance(
                    self.distribution_center.latitude, self.distribution_center.longitude,
                    point['latitude'], point['longitude']
                )
                if distance > max_distance:
                    max_distance = distance
                    start_point = point_idx
            
            if start_point is None:
                break
                
            # Inicia uma nova rota com o ponto mais distante
            current_route = [start_point]
            current_demand = self.points_of_sale.iloc[start_point]['demanda_kg']
            current_stops = 1
            unvisited.remove(start_point)
            
            # Posição atual
            current_lat = self.points_of_sale.iloc[start_point]['latitude']
            current_lon = self.points_of_sale.iloc[start_point]['longitude']
            
            # Tenta adicionar mais pontos à rota
            while unvisited and current_stops < max_stops_per_day:
                # Encontra o ponto não visitado mais próximo que não exceda a capacidade
                min_distance = float('inf')
                nearest_point = None
                
                for point_idx in unvisited:
                    point = self.points_of_sale.iloc[point_idx]
                    # Verifica se adicionar este ponto excederia a capacidade do veículo
                    if current_demand + point['demanda_kg'] > vehicle_capacity:
                        continue
                        
                    distance = self.calculate_distance(
                        current_lat, current_lon,
                        point['latitude'], point['longitude']
                    )
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_point = point_idx
                
                # Se não encontrou nenhum ponto válido, termina a rota atual
                if nearest_point is None:
                    break
                
                # Adiciona o ponto mais próximo à rota
                current_route.append(nearest_point)
                point = self.points_of_sale.iloc[nearest_point]
                current_lat = point['latitude']
                current_lon = point['longitude']
                current_demand += point['demanda_kg']
                current_stops += 1
                unvisited.remove(nearest_point)
            
            # Se formou uma rota, adiciona à lista de rotas
            if current_route:
                routes.append(current_route)
        
        return routes
    
    def calculate_route_costs(self, vehicle: pd.Series, route: List[int] = None) -> Dict[str, float]:
        """
        Calcula os custos de uma rota.
        
        Args:
            vehicle: Série com os dados do veículo
            route: Lista de índices dos pontos de venda na rota. Se None, usa todos os pontos.
        
        Returns:
            Dicionário com os custos fixos, variáveis e totais
        """
        # Se não há rota especificada, retorna custos zerados
        if route is None or len(route) == 0:
            return {
                'fixed': vehicle['Custo fixo por mês'],
                'variable': 0,
                'total': vehicle['Custo fixo por mês'],
                'distance': 0
            }
        
        # Calcula a distância total da rota
        total_distance = 0
        
        # Pega o primeiro ponto da rota
        first_pdv = self.points_of_sale.iloc[route[0]]
        
        # Distância do CD ao primeiro ponto
        total_distance = self.calculate_distance(
            self.distribution_center.latitude, self.distribution_center.longitude,
            first_pdv['latitude'], first_pdv['longitude']
        )
        
        # Distância entre pontos consecutivos
        for i in range(len(route) - 1):
            current_pdv = self.points_of_sale.iloc[route[i]]
            next_pdv = self.points_of_sale.iloc[route[i + 1]]
            total_distance += self.calculate_distance(
                current_pdv['latitude'], current_pdv['longitude'],
                next_pdv['latitude'], next_pdv['longitude']
            )
        
        # Distância do último ponto ao CD
        last_pdv = self.points_of_sale.iloc[route[-1]]
        total_distance += self.calculate_distance(
            last_pdv['latitude'], last_pdv['longitude'],
            self.distribution_center.latitude, self.distribution_center.longitude
        )
        
        # Calcula os custos
        fixed_cost = vehicle['Custo fixo por mês']
        variable_cost = vehicle['Custo variável por km'] * total_distance
        total_cost = fixed_cost + variable_cost
        
        return {
            'fixed': fixed_cost,
            'variable': variable_cost,
            'total': total_cost,
            'distance': total_distance
        } 