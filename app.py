import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from optimizer.logistics_optimizer import LogisticsOptimizer
from utils.sample_data import generate_sample_data

st.set_page_config(page_title="Otimizador Logístico", layout="wide")

st.title("Otimizador de Custos Logísticos")

# Premissas de transporte e CDs
st.header("Premissas")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Modelo de Transporte")
    transport_data = {
        'Modal': ['Van', '03/04', 'Toco', 'Truck', 'Carreta'],
        'Custo fixo por mês': [7000, 11000, 13000, 15000, 20000],
        'Custo variável por km': [1.0, 2.0, 2.5, 3.0, 4.0],
        'Nº entrega por mês': [176, 176, 176, 176, 176],
        'Capacidade por entrega (kg)': [1200, 3000, 7000, 12000, 30000]
    }
    transport_df = pd.DataFrame(transport_data)
    edited_transport = st.data_editor(transport_df, num_rows="fixed")

with col2:
    st.subheader("Centro de Distribuição")
    cd_data = {
        'Tipos de CD': ['CD pequeno', 'CD médio', 'CD grande'],
        'Capacidade (kg)': [150000, 500000, 1500000],
        'Custo mensal': [20000, 30000, 50000]
    }
    cd_df = pd.DataFrame(cd_data)
    edited_cd = st.data_editor(cd_df, num_rows="fixed")

# Adiciona uma linha separadora
st.markdown("---")

# Sidebar para upload e configurações
with st.sidebar:
    st.header("Configurações")
    
    # Opção para usar dados de exemplo
    use_sample_data = st.checkbox("Usar dados de exemplo", value=False)
    
    if use_sample_data:
        num_points = st.number_input("Número de pontos de venda", min_value=10, max_value=1000, value=100)
        data = generate_sample_data(num_points)
    else:
        # Upload do arquivo
        uploaded_file = st.file_uploader(
            "Upload da base de dados (CSV com colunas: latitude, longitude, demanda_kg)",
            type="csv"
        )
    
    # Configurações dos CDs
    num_cds = st.number_input("Número de CDs", min_value=1, max_value=10, value=4)
    cd_sizes = st.multiselect(
        "Tamanhos dos CDs",
        options=["pequeno", "medio", "grande"],
        default=["medio"] * num_cds
    )

# Área principal
if use_sample_data or uploaded_file is not None:
    try:
        # Carrega os dados se não estiver usando dados de exemplo
        if not use_sample_data:
            data = pd.read_csv(uploaded_file)
        
        # Verifica as colunas necessárias
        required_columns = ['latitude', 'longitude', 'demanda_kg']
        if not all(col in data.columns for col in required_columns):
            st.error("O arquivo CSV deve conter as colunas: latitude, longitude, demanda_kg")
        else:
            # Exibe estatísticas dos dados
            st.subheader("Estatísticas dos Dados")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Pontos de Venda", len(data))
            with col2:
                st.metric("Demanda Total (kg)", f"{data['demanda_kg'].sum():,.0f}")
            with col3:
                st.metric("Demanda Média (kg)", f"{data['demanda_kg'].mean():,.0f}")
            
            # Inicializa e executa o otimizador
            optimizer = LogisticsOptimizer(
                pdv_data=data,
                transport_data=edited_transport,
                cd_data=edited_cd
            )
            
            with st.spinner("Otimizando a rede logística..."):
                solution = optimizer.optimize(num_cds=num_cds, cd_sizes=cd_sizes)
            
            # Exibe resultados
            st.subheader("Resultados da Otimização")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Custos Mensais**")
                st.write(f"Custo de Transporte: R$ {solution['costs']['transport']:,.2f}")
                st.write(f"Custo de Armazenagem: R$ {solution['costs']['storage']:,.2f}")
                st.write(f"Custo Total: R$ {solution['costs']['total']:,.2f}")
            
            with col2:
                st.write("**Alocação de Veículos**")
                for vehicle, count in solution['vehicles'].items():
                    st.write(f"{vehicle}: {count}")
            
            # Mapa
            st.subheader("Visualização da Rede")
            map_solution = optimizer.visualize_solution()
            if map_solution:
                folium_static(map_solution)
                
    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")
else:
    st.info("Por favor, faça o upload de um arquivo CSV com os dados dos pontos de venda ou use dados de exemplo.") 