# Otimizador de Custos Logísticos

Este é um aplicativo web desenvolvido com Streamlit para otimização de custos logísticos. O aplicativo permite:

- Configurar modelos de transporte (Van, 03/04, Toco, Truck, Carreta)
- Definir centros de distribuição (CDs)
- Otimizar a distribuição de produtos
- Visualizar resultados em um mapa interativo

## Instalação

1. Clone este repositório
2. Crie um ambiente virtual:
```bash
python -m venv venv
```
3. Ative o ambiente virtual:
- Windows:
```bash
.\venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```
4. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Executar

Para rodar o aplicativo localmente:

```bash
streamlit run app.py
```

O aplicativo estará disponível em `http://localhost:8501`

## Funcionalidades

- Configuração de modelos de transporte
- Definição de centros de distribuição
- Upload de dados de pontos de venda
- Geração de dados de exemplo
- Visualização de resultados em mapa
- Cálculo de custos otimizados

## Requisitos

- Python 3.8+
- Dependências listadas em `requirements.txt`

## Estrutura do Projeto

```
.
├── app.py                  # Aplicativo Streamlit
├── requirements.txt        # Dependências do projeto
└── src/
    ├── models/            # Classes de modelo
    │   ├── vehicle.py
    │   └── distribution_center.py
    ├── optimizer/         # Lógica de otimização
    │   └── logistics_optimizer.py
    └── utils/            # Funções utilitárias
        └── distance_calculator.py
```

## Limitações do MVP

- Utiliza um algoritmo simplificado de otimização
- Não considera restrições de tempo de entrega
- Assume demanda constante
- Não considera variações sazonais
- Não inclui otimização de rotas detalhada

## Próximos Passos

- Implementar algoritmo de otimização mais sofisticado
- Adicionar restrições de janelas de tempo
- Incluir variações sazonais de demanda
- Adicionar otimização de rotas
- Implementar mais métricas e análises
- Adicionar exportação de relatórios 