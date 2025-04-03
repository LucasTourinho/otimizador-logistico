import pandas as pd
from typing import List

class Factory:
    def __init__(self, name: str, latitude: float, longitude: float, monthly_capacity: float):
        """
        Inicializa uma fábrica
        
        Args:
            name: Nome da fábrica
            latitude: Latitude da fábrica
            longitude: Longitude da fábrica
            monthly_capacity: Capacidade mensal de produção em kg
        """
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.monthly_capacity = monthly_capacity
    
    def __str__(self) -> str:
        return f"Fábrica {self.name} (Capacidade: {self.monthly_capacity:,.0f} kg/mês)"
    
    @staticmethod
    def create_from_dataframe(df: pd.DataFrame) -> List['Factory']:
        """
        Cria uma lista de fábricas a partir de um DataFrame
        
        Args:
            df: DataFrame com colunas: Nome, Latitude, Longitude, Capacidade (kg)
            
        Returns:
            Lista de objetos Factory
        """
        factories = []
        for _, row in df.iterrows():
            factory = Factory(
                name=row['Nome'],
                latitude=row['Latitude'],
                longitude=row['Longitude'],
                monthly_capacity=row['Capacidade (kg)']
            )
            factories.append(factory)
        return factories 