import pandas as pd
import numpy as np
from pulp import *
from sklearn.cluster import KMeans
import folium
from models.vehicle import Vehicle
from models.distribution_center import DistributionCenter
from utils.distance_calculator import haversine_distance

class LogisticsOptimizer:
    def __init__(self, pdv_data, transport_data, cd_data):
        """
        Inicializa o otimizador logístico
        
        Args:
            pdv_data: DataFrame com dados dos pontos de venda
            transport_data: DataFrame com configurações de transporte
            cd_data: DataFrame com configurações dos CDs
        """
        self.pdv_data = pdv_data
        self.vehicles = Vehicle.get_available_vehicles(transport_data)
        self.cd_data = cd_data
        self.current_solution = None
        
    def optimize(self, num_cds=4, cd_sizes=None):
        """
        Executa a otimização da rede logística usando k-means para posicionamento dos CDs
        """
        if cd_sizes is None:
            cd_sizes = ['medio'] * num_cds
            
        # 1. Determinar localizações dos CDs usando k-means
        coords = self.pdv_data[['latitude', 'longitude']].values
        kmeans = KMeans(n_clusters=num_cds, random_state=42)
        cluster_labels = kmeans.fit_predict(coords)
        
        # Criar os CDs nas posições centrais dos clusters
        self.current_solution = {
            'cds': [],
            'allocations': {},
            'vehicles': {},
            'costs': {
                'transport': 0,
                'storage': 0,
                'total': 0
            }
        }
        
        # 2. Criar os CDs e alocar PDVs
        for i, (lat, lon) in enumerate(kmeans.cluster_centers_):
            cd = DistributionCenter(cd_sizes[i], lat, lon, self.cd_data)
            self.current_solution['cds'].append(cd)
            
            # Encontrar PDVs deste cluster
            cluster_pdvs = self.pdv_data[cluster_labels == i]
            total_demand = cluster_pdvs['demanda_kg'].sum()
            
            # Verificar se a capacidade do CD é suficiente
            if total_demand > cd.capacity:
                cd = DistributionCenter('grande', lat, lon, self.cd_data)
                self.current_solution['cds'][i] = cd
            
            # Alocar PDVs ao CD
            self.current_solution['allocations'][i] = cluster_pdvs.index.tolist()
            
            # 3. Selecionar veículos apropriados
            vehicle = self._select_best_vehicle(total_demand / 22)  # Assumindo 22 dias úteis
            self.current_solution['vehicles'][vehicle.name] = self.current_solution['vehicles'].get(vehicle.name, 0) + 1
            
            # 4. Calcular custos
            # Custo de armazenagem
            self.current_solution['costs']['storage'] += cd.monthly_cost
            
            # Custo de transporte
            total_distance = sum(haversine_distance(
                cd.latitude, cd.longitude,
                row['latitude'], row['longitude']
            ) * 2 for _, row in cluster_pdvs.iterrows())  # Ida e volta
            
            self.current_solution['costs']['transport'] += vehicle.calculate_cost(total_distance)
        
        self.current_solution['costs']['total'] = (
            self.current_solution['costs']['transport'] +
            self.current_solution['costs']['storage']
        )
        
        return self.current_solution
    
    def _select_best_vehicle(self, total_demand):
        """Seleciona o menor veículo capaz de atender a demanda"""
        for vehicle in sorted(self.vehicles, key=lambda v: v.capacity_kg):
            if vehicle.capacity_kg >= total_demand:
                return vehicle
        return self.vehicles[-1]  # Retorna o maior veículo se nenhum outro for adequado
    
    def visualize_solution(self):
        """
        Gera visualização da solução usando folium
        """
        if not self.current_solution:
            return None
            
        # Criar mapa centralizado na média das coordenadas
        center_lat = self.pdv_data['latitude'].mean()
        center_lon = self.pdv_data['longitude'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
        
        # Cores para cada cluster
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
                 'lightred', 'beige', 'darkblue', 'darkgreen']
                 
        # Adicionar CDs
        for i, cd in enumerate(self.current_solution['cds']):
            folium.Marker(
                [cd.latitude, cd.longitude],
                popup=f"CD {i+1}: {cd.size.capitalize()}\nCapacidade: {cd.capacity:,}kg",
                icon=folium.Icon(color='black', icon='info-sign')
            ).add_to(m)
            
            # Adicionar PDVs deste cluster
            cluster_pdvs = self.pdv_data.loc[self.current_solution['allocations'][i]]
            for _, pdv in cluster_pdvs.iterrows():
                folium.CircleMarker(
                    [pdv['latitude'], pdv['longitude']],
                    radius=5,
                    popup=f"Demanda: {pdv['demanda_kg']:,}kg",
                    color=colors[i % len(colors)],
                    fill=True
                ).add_to(m)
                
                # Linha conectando PDV ao CD
                folium.PolyLine(
                    locations=[[cd.latitude, cd.longitude], 
                             [pdv['latitude'], pdv['longitude']]],
                    color=colors[i % len(colors)],
                    weight=1,
                    opacity=0.5
                ).add_to(m)
        
        return m 