import pandas as pd
import numpy as np

def generate_sample_data(num_points=100):
    """
    Gera dados de exemplo para teste do otimizador
    
    Args:
        num_points: Número de pontos de venda a serem gerados
        
    Returns:
        DataFrame com colunas: latitude, longitude, demanda_kg
    """
    # Região aproximada do Brasil central
    lat_min, lat_max = -20, -10
    lon_min, lon_max = -55, -45
    
    # Gerar coordenadas aleatórias
    latitudes = np.random.uniform(lat_min, lat_max, num_points)
    longitudes = np.random.uniform(lon_min, lon_max, num_points)
    
    # Gerar demandas aleatórias (entre 100kg e 5000kg)
    demandas = np.random.uniform(100, 5000, num_points)
    
    # Criar DataFrame
    df = pd.DataFrame({
        'latitude': latitudes,
        'longitude': longitudes,
        'demanda_kg': demandas
    })
    
    return df 