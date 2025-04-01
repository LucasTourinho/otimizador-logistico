from setuptools import setup, find_packages

setup(
    name="logistics_optimizer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'pandas',
        'folium',
        'streamlit-folium',
        'pulp',
        'scikit-learn',
        'numpy'
    ],
) 