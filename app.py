import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from optimizer.logistics_optimizer import LogisticsOptimizer
from utils.sample_data import generate_sample_data
from models.factory import Factory
import streamlit.components.v1 as components

st.set_page_config(page_title="Otimizador Logístico", layout="wide")

# Adiciona os scripts de rastreamento
tracking_code = """
<!-- Microsoft Clarity -->
<script type="text/javascript">
    (function(c,l,a,r,i,t,y){
        c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    })(window, document, "clarity", "script", "qyibov06ee");
</script>

<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-5BSM0CNH9W"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-5BSM0CNH9W');
</script>
"""

# Injeta os scripts de rastreamento
components.html(tracking_code, height=0)

st.title("Otimizador de Custos Logísticos")

# Premissas de transporte, CDs e Fábricas
st.header("Premissas")
col1, col2, col3 = st.columns(3)

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

with col3:
    st.subheader("Fábricas")
    factory_data = {
        'Nome': ['Fábrica 1'],
        'Latitude': [-23.5505],
        'Longitude': [-46.6333],
        'Capacidade (kg)': [2000000]
    }
    factory_df = pd.DataFrame(factory_data)
    edited_factory = st.data_editor(factory_df, num_rows="dynamic")

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
    
    # Remove a seleção de tamanhos e usa sempre o maior CD possível
    cd_data = {
        'Tipos de CD': ['CD grande'] * num_cds,  # Começa com CDs grandes
        'Capacidade (kg)': [1500000] * num_cds,
        'Custo mensal': [50000] * num_cds
    }
    edited_cd = pd.DataFrame(cd_data)

# Configuração do Cenário Atual
st.header("Cenário Atual")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Frota Atual")
    current_fleet_data = {
        'Modal': ['Van', '03/04', 'Toco', 'Truck', 'Carreta'],
        'Quantidade': [0, 0, 0, 0, 0]  # Usuário define quantidade de cada tipo
    }
    current_fleet_df = pd.DataFrame(current_fleet_data)
    edited_current_fleet = st.data_editor(current_fleet_df, num_rows="fixed")

with col2:
    st.subheader("CDs Atuais")
    current_cd_data = {
        'Nome': ['CD 1'],
        'Latitude': [-23.5505],
        'Longitude': [-46.6333],
        'Tamanho': ['CD grande']
    }
    current_cd_df = pd.DataFrame(current_cd_data)
    edited_current_cd = st.data_editor(
        current_cd_df,
        num_rows="dynamic",
        column_config={
            "Tamanho": st.column_config.SelectboxColumn(
                options=["CD pequeno", "CD médio", "CD grande"]
            )
        }
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
                total_demand = data['demanda_kg'].sum()
                st.metric("Demanda Total (kg)", f"{total_demand:,.0f}")
            with col3:
                st.metric("Demanda Média (kg)", f"{data['demanda_kg'].mean():,.0f}")
            
            # Ajusta o tamanho dos CDs com base na demanda
            demanda_por_cd = total_demand / num_cds
            
            # Define o tamanho ideal dos CDs
            if demanda_por_cd <= 150000:  # Capacidade do CD pequeno
                cd_data = {
                    'Tipos de CD': ['CD pequeno'] * num_cds,
                    'Capacidade (kg)': [150000] * num_cds,
                    'Custo mensal': [20000] * num_cds
                }
            elif demanda_por_cd <= 500000:  # Capacidade do CD médio
                cd_data = {
                    'Tipos de CD': ['CD médio'] * num_cds,
                    'Capacidade (kg)': [500000] * num_cds,
                    'Custo mensal': [30000] * num_cds
                }
            else:  # Mantém CD grande
                cd_data = {
                    'Tipos de CD': ['CD grande'] * num_cds,
                    'Capacidade (kg)': [1500000] * num_cds,
                    'Custo mensal': [50000] * num_cds
                }
            
            edited_cd = pd.DataFrame(cd_data)
            
            # Criar lista de fábricas
            factories = Factory.create_from_dataframe(edited_factory)
            
            # Calcular cenário atual
            st.header("Cenário Atual")
            with st.spinner("Calculando cenário atual..."):
                # Prepara os dados dos CDs atuais
                current_cd_data = pd.DataFrame([{
                    'Tipos de CD': row['Tamanho'],
                    'Capacidade (kg)': cd_df[cd_df['Tipos de CD'] == row['Tamanho']]['Capacidade (kg)'].iloc[0],
                    'Custo mensal': cd_df[cd_df['Tipos de CD'] == row['Tamanho']]['Custo mensal'].iloc[0]
                } for _, row in edited_current_cd.iterrows()])

                current_optimizer = LogisticsOptimizer(
                    pdv_data=data,
                    transport_data=edited_transport,
                    cd_data=current_cd_data,
                    factories=factories
                )
                current_solution = current_optimizer.optimize(fixed_fleet=edited_current_fleet)

            # Calcular cenário proposto
            st.header("Cenário Proposto")
            with st.spinner("Otimizando cenário proposto..."):
                optimizer = LogisticsOptimizer(
                    pdv_data=data,
                    transport_data=edited_transport,
                    cd_data=edited_cd,
                    factories=factories
                )
                proposed_solution = optimizer.optimize()

            if current_solution and proposed_solution:
                # Exibe comparativo de resultados
                st.header("Comparativo de Cenários")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Cenário Atual")
                    st.write("**Custos Mensais**")
                    st.write(f"Custo de Transporte: R$ {current_solution['transport_costs']:,.2f}")
                    st.write(f"Custo de Armazenagem: R$ {current_solution['storage_costs']:,.2f}")
                    st.write(f"Custo Total: R$ {current_solution['total_cost']:,.2f}")
                    
                    st.write("**Alocação de Veículos**")
                    for modal, count in current_solution['vehicles'].items():
                        if count > 0:
                            rotas = current_solution['routes_per_vehicle'].get(modal, 0)
                            st.write(f"{modal}:")
                            st.write(f"- Veículos necessários: {count}")
                            st.write(f"- Total de rotas: {rotas}")
                            st.write(f"- Média de rotas por veículo/dia: {rotas/(count*22):.1f}")
                            st.write("---")

                with col2:
                    st.subheader("Cenário Proposto")
                    st.write("**Custos Mensais**")
                    st.write(f"Custo de Transporte: R$ {proposed_solution['transport_costs']:,.2f}")
                    st.write(f"Custo de Armazenagem: R$ {proposed_solution['storage_costs']:,.2f}")
                    st.write(f"Custo Total: R$ {proposed_solution['total_cost']:,.2f}")
                    
                    st.write("**Alocação de Veículos**")
                    for modal, count in proposed_solution['vehicles'].items():
                        if count > 0:
                            rotas = proposed_solution['routes_per_vehicle'].get(modal, 0)
                            st.write(f"{modal}:")
                            st.write(f"- Veículos necessários: {count}")
                            st.write(f"- Total de rotas: {rotas}")
                            st.write(f"- Média de rotas por veículo/dia: {rotas/(count*22):.1f}")
                            st.write("---")

                # Calcula e mostra a economia
                economia = current_solution['total_cost'] - proposed_solution['total_cost']
                economia_percentual = (economia / current_solution['total_cost']) * 100
                
                st.header("Economia Potencial")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Economia Mensal", f"R$ {economia:,.2f}")
                with col2:
                    st.metric("Economia Percentual", f"{economia_percentual:.1f}%")

                # Visualização dos mapas
                st.header("Visualização da Rede")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Cenário Atual")
                    current_map = current_optimizer.visualize_solution(current_solution)
                    if current_map:
                        folium_static(current_map)
                    else:
                        st.error('Não foi possível gerar o mapa do cenário atual.')

                with col2:
                    st.subheader("Cenário Proposto")
                    proposed_map = optimizer.visualize_solution(proposed_solution)
                    if proposed_map:
                        folium_static(proposed_map)
                    else:
                        st.error('Não foi possível gerar o mapa do cenário proposto.')

            else:
                st.error("Não foi possível gerar uma solução válida para um dos cenários.")
                
    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")
else:
    st.info("Por favor, faça o upload de um arquivo CSV com os dados dos pontos de venda ou use dados de exemplo.") 