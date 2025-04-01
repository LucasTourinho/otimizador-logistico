class DistributionCenter:
    def __init__(self, size, latitude, longitude, cd_data):
        """
        Inicializa um centro de distribuição
        
        Args:
            size: Tamanho do CD ('pequeno', 'medio', 'grande')
            latitude: Latitude do CD
            longitude: Longitude do CD
            cd_data: DataFrame com as configurações dos CDs
        """
        self.size = size
        self.latitude = latitude
        self.longitude = longitude
        
        # Mapeamento dos tamanhos para os nomes no DataFrame
        size_map = {
            'pequeno': 'CD pequeno',
            'medio': 'CD médio',
            'grande': 'CD grande'
        }
        
        # Encontrar dados do CD pelo tamanho
        cd_info = cd_data[cd_data['Tipos de CD'] == size_map[self.size]].iloc[0]
        self.capacity = cd_info['Capacidade (kg)']
        self.monthly_cost = cd_info['Custo mensal']

    def __str__(self):
        return f"CD {self.size.capitalize()} (Lat: {self.latitude:.4f}, Long: {self.longitude:.4f})"
