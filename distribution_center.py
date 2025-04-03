class DistributionCenter:
    """Representa um centro de distribuição."""
    
    def __init__(self, latitude: float, longitude: float, size: str, monthly_cost: float):
        """
        Inicializa um centro de distribuição.
        
        Args:
            latitude: Latitude do CD
            longitude: Longitude do CD
            size: Tamanho do CD (pequeno, médio, grande)
            monthly_cost: Custo mensal do CD
        """
        self.latitude = latitude
        self.longitude = longitude
        self.size = size
        self.monthly_cost = monthly_cost
    
    def __str__(self) -> str:
        """Retorna uma representação em string do CD."""
        return f"CD {self.size} em ({self.latitude}, {self.longitude})" 