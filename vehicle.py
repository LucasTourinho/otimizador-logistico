class Vehicle:
    def __init__(self, name, fixed_cost, variable_cost_per_km, deliveries_per_month, capacity_kg):
        self.name = name
        self.fixed_cost = fixed_cost
        self.variable_cost_per_km = variable_cost_per_km
        self.deliveries_per_month = deliveries_per_month
        self.capacity_kg = capacity_kg

    def calculate_cost(self, distance_km):
        """Calcula o custo total para uma determinada distância"""
        return self.fixed_cost + (self.variable_cost_per_km * distance_km)

    @staticmethod
    def get_available_vehicles(transport_data):
        """
        Retorna a lista de veículos disponíveis com suas características atualizadas
        
        Args:
            transport_data: DataFrame com as configurações de transporte
        """
        vehicles = []
        for _, row in transport_data.iterrows():
            vehicles.append(Vehicle(
                name=row['Modal'],
                fixed_cost=row['Custo fixo por mês'],
                variable_cost_per_km=row['Custo variável por km'],
                deliveries_per_month=row['Nº entrega por mês'],
                capacity_kg=row['Capacidade por entrega (kg)']
            ))
        return vehicles

    def __str__(self):
        return f"{self.name} (Capacidade: {self.capacity_kg}kg)" 