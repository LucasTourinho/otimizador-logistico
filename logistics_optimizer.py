import pandas as pd
import numpy as np
from pulp import *
from sklearn.cluster import KMeans
import folium
from models.vehicle import Vehicle
from models.distribution_center import DistributionCenter
from utils.distance_calculator import haversine_distance
from models.factory import Factory
from optimizer.route_optimizer import RouteOptimizer
from typing import List, Dict, Any
import math
import streamlit as st

class LogisticsOptimizer:
    def __init__(self, pdv_data: pd.DataFrame, transport_data: pd.DataFrame, cd_data: pd.DataFrame, factories: List[Factory]):
        """
        Inicializa o otimizador logístico
        
        Args:
            pdv_data: DataFrame com dados dos pontos de venda
            transport_data: DataFrame com configurações de transporte
            cd_data: DataFrame com configurações dos CDs
            factories: Lista de fábricas
        """
        self.pdv_data = pdv_data
        self.transport_data = transport_data
        self.cd_data = cd_data
        self.factories = factories
        self.solution = None
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula a distância em km entre dois pontos usando a fórmula de Haversine."""
        R = 6371  # Raio da Terra em km
        
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c

    def find_best_vehicle_mix(self, cluster_points: pd.DataFrame, route_optimizer: RouteOptimizer, fixed_fleet=None) -> Dict:
        """
        Encontra o melhor mix de veículos ou usa a frota fixa definida pelo usuário.
        
        Args:
            cluster_points: DataFrame com os pontos de venda do cluster
            route_optimizer: Otimizador de rotas para o cluster
            fixed_fleet: DataFrame com a frota fixa definida pelo usuário
        """
        if len(cluster_points) == 0:
            return None

        if fixed_fleet is not None:
            # Usa a frota definida pelo usuário
            total_cost = 0
            vehicles_used = {}
            all_routes = []

            # Para cada tipo de veículo definido pelo usuário
            for _, row in fixed_fleet.iterrows():
                if row['Quantidade'] > 0:
                    # Obtém dados do veículo
                    vehicle_data = self.transport_data[self.transport_data['Modal'] == row['Modal']].iloc[0]
                    
                    # Tenta criar rotas com este veículo
                    routes = route_optimizer.optimize_routes(
                        vehicle_capacity=vehicle_data['Capacidade por entrega (kg)'],
                        max_stops_per_day=8
                    )
                    
                    if routes:
                        # Calcula custos variáveis (km rodado)
                        route_cost = 0
                        for route in routes:
                            costs = route_optimizer.calculate_route_costs(vehicle_data, route)
                            route_cost += costs['variable']
                        
                        # Adiciona custo fixo da frota
                        fixed_cost = row['Quantidade'] * vehicle_data['Custo fixo por mês']
                        total_cost += route_cost + fixed_cost
                        
                        vehicles_used[row['Modal']] = {
                            'count': row['Quantidade'],
                            'routes': routes
                        }
                        all_routes.extend(routes)

            if vehicles_used:
                return {
                    'routes': all_routes,
                    'vehicles': vehicles_used,
                    'total_cost': total_cost
                }
            return None

        else:
            # Calcula a demanda total e média por ponto
            total_demand = cluster_points['demanda_kg'].sum()
            avg_demand_per_point = total_demand / len(cluster_points)
            
            # Ordena veículos por capacidade (do maior para o menor)
            vehicles = self.transport_data.sort_values('Capacidade por entrega (kg)', ascending=False)
            
            # Tenta encontrar o veículo mais adequado
            for _, vehicle in vehicles.iterrows():
                # Calcula quantos pontos podem ser atendidos por rota baseado na capacidade
                max_stops_by_capacity = vehicle['Capacidade por entrega (kg)'] / avg_demand_per_point
                
                # Se o veículo pode fazer pelo menos 4 paradas por rota (aumentamos o mínimo)
                if max_stops_by_capacity >= 4:
                    # Tenta roteirizar com este veículo
                    routes = route_optimizer.optimize_routes(
                        vehicle_capacity=vehicle['Capacidade por entrega (kg)'],
                        max_stops_per_day=8  # Fixamos em 8 paradas por rota
                    )
                    
                    if routes:
                        # Verifica se as rotas estão eficientes (média de paradas >= 3)
                        avg_stops_per_route = sum(len(route) for route in routes) / len(routes)
                        if avg_stops_per_route < 3:
                            continue
                        
                        # Calcula custos
                        total_cost = 0
                        for route in routes:
                            costs = route_optimizer.calculate_route_costs(vehicle, route)
                            total_cost += costs['variable']
                        
                        # Adiciona custo fixo pelo número de veículos necessários
                        deliveries_per_month = vehicle['Nº entrega por mês']
                        num_vehicles = math.ceil(len(routes) / (deliveries_per_month))
                        total_cost += num_vehicles * vehicle['Custo fixo por mês']
                        
                        # Retorna a solução
                        return {
                            'routes': routes,
                            'vehicles': {
                                vehicle['Modal']: {
                                    'count': num_vehicles,
                                    'routes': routes
                                }
                            },
                            'total_cost': total_cost
                        }
            
            # Se nenhum veículo funcionou com rotas eficientes, tenta novamente com critérios mais flexíveis
            vehicle = vehicles.iloc[0]  # Pega o maior veículo
            routes = route_optimizer.optimize_routes(
                vehicle_capacity=vehicle['Capacidade por entrega (kg)'],
                max_stops_per_day=8  # Mantém 8 paradas por rota
            )
            
            if routes:
                # Calcula custos
                total_cost = 0
                for route in routes:
                    costs = route_optimizer.calculate_route_costs(vehicle, route)
                    total_cost += costs['variable']
                
                # Adiciona custo fixo pelo número de veículos necessários
                deliveries_per_month = vehicle['Nº entrega por mês']
                num_vehicles = math.ceil(len(routes) / deliveries_per_month)
                total_cost += num_vehicles * vehicle['Custo fixo por mês']
                
                return {
                    'routes': routes,
                    'vehicles': {
                        vehicle['Modal']: {
                            'count': num_vehicles,
                            'routes': routes
                        }
                    },
                    'total_cost': total_cost
                }
            
            return None

    def optimize(self, fixed_fleet=None) -> Dict:
        """
        Otimiza a distribuição dos pontos de venda entre os CDs.
        
        Args:
            fixed_fleet: DataFrame com a frota fixa definida pelo usuário (para cenário atual)
        """
        try:
            # Prepara os dados para clusterização
            X = self.pdv_data[['latitude', 'longitude']].values
            
            # Inicializa o modelo de clusterização
            kmeans = KMeans(n_clusters=len(self.cd_data))
            
            # Realiza a clusterização
            clusters = kmeans.fit_predict(X)
            
            # Cria os centros de distribuição
            self.distribution_centers = []
            for i in range(len(self.cd_data)):
                centroid = kmeans.cluster_centers_[i]
                cd = DistributionCenter(
                    latitude=centroid[0],
                    longitude=centroid[1],
                    size=self.cd_data.iloc[i]['Tipos de CD'],
                    monthly_cost=self.cd_data.iloc[i]['Custo mensal']
                )
                self.distribution_centers.append(cd)
            
            # Inicializa contadores
            transport_costs = 0
            storage_costs = sum(cd.monthly_cost for cd in self.distribution_centers)
            vehicle_counts = {vehicle['Modal']: 0 for _, vehicle in self.transport_data.iterrows()}
            vehicle_routes = {vehicle['Modal']: 0 for _, vehicle in self.transport_data.iterrows()}
            
            # Armazena as soluções de roteamento para cada CD
            routing_solutions = []
            
            # Calcula os custos de transporte
            for i, cd in enumerate(self.distribution_centers):
                # Encontra a fábrica mais próxima deste CD
                closest_factory = min(self.factories, 
                                    key=lambda f: self.calculate_distance(f.latitude, f.longitude, cd.latitude, cd.longitude))
                
                # Pontos de venda atribuídos a este CD
                cluster_points = self.pdv_data[clusters == i]
                
                # Otimiza as rotas para este cluster
                route_optimizer = RouteOptimizer(
                    factory=closest_factory,
                    distribution_center=cd,
                    points_of_sale=cluster_points
                )
                
                # Encontra o melhor mix de veículos ou usa frota fixa
                solution = self.find_best_vehicle_mix(
                    cluster_points=cluster_points,
                    route_optimizer=route_optimizer,
                    fixed_fleet=fixed_fleet
                )
                
                if solution:
                    transport_costs += solution['total_cost']
                    # Atualiza contadores de veículos e rotas
                    for modal, info in solution['vehicles'].items():
                        vehicle_counts[modal] += info['count']
                        vehicle_routes[modal] += len(info['routes'])
                    
                    # Armazena a solução de roteamento
                    routing_solutions.append({
                        'cd_index': i,
                        'closest_factory': closest_factory,
                        'cluster_points': cluster_points,
                        'solution': solution
                    })
            
            # Verifica se encontrou alguma solução
            if not routing_solutions:
                st.error("Não foi possível encontrar uma solução viável com os parâmetros fornecidos.")
                return None
            
            # Calcula o custo total
            total_cost = transport_costs + storage_costs
            
            # Armazena a solução
            self.solution = {
                'clusters': clusters,
                'transport_costs': transport_costs,
                'storage_costs': storage_costs,
                'total_cost': total_cost,
                'vehicles': vehicle_counts,
                'routes_per_vehicle': {modal: routes for modal, routes in vehicle_routes.items() if routes > 0},
                'routing_solutions': routing_solutions
            }
            
            return self.solution
            
        except Exception as e:
            st.error(f"Erro durante a otimização: {str(e)}")
            return None
    
    def visualize_solution(self, solution: Dict) -> folium.Map:
        """Visualiza a solução em um mapa interativo."""
        if not self.solution or 'routing_solutions' not in self.solution:
            raise ValueError("Execute optimize() antes de visualizar")
            
        # Cria o mapa centralizado na média das coordenadas dos CDs
        cd_lat = np.mean([cd.latitude for cd in self.distribution_centers])
        cd_lon = np.mean([cd.longitude for cd in self.distribution_centers])
        m = folium.Map(location=[cd_lat, cd_lon], zoom_start=6)
        
        # Cores para cada CD
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'darkblue', 'darkgreen', 'cadetblue', 'lightred']
        
        # Cria grupos de camadas para o controle de visualização
        factory_group = folium.FeatureGroup(name='Fábricas').add_to(m)
        cd_group = folium.FeatureGroup(name='Centros de Distribuição').add_to(m)
        route_groups = {}
        
        # Adiciona as fábricas
        for factory in self.factories:
            folium.Marker(
                [factory.latitude, factory.longitude],
                popup=folium.Popup(f"""
                    <b>Fábrica {factory.name}</b>
                """, max_width=200),
                icon=folium.Icon(color='black', icon='industry', prefix='fa'),
            ).add_to(factory_group)
        
        # Processa cada solução de roteamento
        for routing_solution in self.solution['routing_solutions']:
            i = routing_solution['cd_index']
            cd = self.distribution_centers[i]
            closest_factory = routing_solution['closest_factory']
            cluster_points = routing_solution['cluster_points']
            solution = routing_solution['solution']
            
            color = colors[i % len(colors)]
            route_groups[f'Rotas CD {i+1}'] = folium.FeatureGroup(name=f'Rotas CD {i+1}').add_to(m)
            
            # Adiciona o CD
            folium.Marker(
                [cd.latitude, cd.longitude],
                popup=folium.Popup(f"""
                    <b>CD {cd.size}</b><br>
                    Custo mensal: R$ {cd.monthly_cost:,.2f}
                """, max_width=200),
                icon=folium.Icon(color=color, icon='building', prefix='fa'),
            ).add_to(cd_group)
            
            # Adiciona linha da fábrica ao CD (transporte em massa)
            folium.PolyLine(
                locations=[[closest_factory.latitude, closest_factory.longitude],
                          [cd.latitude, cd.longitude]],
                color=color,
                weight=2.5,
                popup='Transporte em massa',
                opacity=0.8
            ).add_to(route_groups[f'Rotas CD {i+1}'])
            
            # Desenha as rotas
            for modal, info in solution['vehicles'].items():
                routes = info['routes']
                for route_idx, route in enumerate(routes):
                    # Cria a lista de coordenadas para a rota
                    route_coords = []
                    
                    # Começa no CD
                    route_coords.append([cd.latitude, cd.longitude])
                    
                    # Adiciona os PDVs na ordem da rota
                    total_demand = 0
                    for stop_num, pdv_idx in enumerate(route, 1):
                        pdv = cluster_points.iloc[pdv_idx]
                        route_coords.append([pdv['latitude'], pdv['longitude']])
                        total_demand += pdv['demanda_kg']
                        
                        # Adiciona marcador do PDV com número da rota
                        circle = folium.CircleMarker(
                            location=[pdv['latitude'], pdv['longitude']],
                            radius=4,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.7,
                            popup=folium.Popup(f"""
                                <b>PDV {pdv.name}</b><br>
                                Rota {route_idx + 1} - Parada {stop_num}<br>
                                Demanda: {pdv['demanda_kg']:,.0f} kg<br>
                                Veículo: {modal}
                            """, max_width=200)
                        ).add_to(route_groups[f'Rotas CD {i+1}'])
                        
                        # Adiciona o número da rota sobre o círculo
                        folium.DivIcon(
                            html=f'''
                                <div style="
                                    background-color: {color};
                                    color: white;
                                    border-radius: 50%;
                                    text-align: center;
                                    width: 16px;
                                    height: 16px;
                                    line-height: 16px;
                                    font-size: 10px;
                                    margin-left: -8px;
                                    margin-top: -8px;
                                ">{route_idx + 1}</div>
                            '''
                        ).add_to(folium.Marker(
                            location=[pdv['latitude'], pdv['longitude']],
                            icon=folium.DivIcon()
                        ).add_to(route_groups[f'Rotas CD {i+1}']))
                    
                    # Retorna ao CD
                    route_coords.append([cd.latitude, cd.longitude])
                    
                    # Desenha a rota com setas direcionais
                    folium.PolyLine(
                        locations=route_coords,
                        color=color,
                        weight=2,
                        popup=folium.Popup(f"""
                            <b>Rota {route_idx + 1}</b><br>
                            Veículo: {modal}<br>
                            Demanda total: {total_demand:,.0f} kg<br>
                            Número de paradas: {len(route)}
                        """, max_width=200),
                        opacity=0.8
                    ).add_to(route_groups[f'Rotas CD {i+1}'])
                    
                    # Adiciona setas direcionais ao longo da rota
                    for j in range(len(route_coords) - 1):
                        points = [(route_coords[j][0], route_coords[j][1]),
                                (route_coords[j+1][0], route_coords[j+1][1])]
                        
                        # Calcula o ponto médio para posicionar a seta
                        mid_point = [
                            (points[0][0] + points[1][0]) / 2,
                            (points[0][1] + points[1][1]) / 2
                        ]
                        
                        # Calcula o ângulo da rota para rotacionar a seta
                        angle = np.degrees(np.arctan2(
                            points[1][0] - points[0][0],
                            points[1][1] - points[0][1]
                        ))
                        
                        # Adiciona a seta no ponto médio
                        folium.RegularPolygonMarker(
                            location=mid_point,
                            color=color,
                            number_of_sides=3,
                            radius=6,
                            rotation=angle,
                            popup=f'Rota {route_idx + 1}'
                        ).add_to(route_groups[f'Rotas CD {i+1}'])
        
        # Adiciona controle de camadas
        folium.LayerControl().add_to(m)
        
        return m 