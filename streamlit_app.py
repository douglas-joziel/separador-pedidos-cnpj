import streamlit as st

pg = st.navigation(
    {
        "Ferramentas": [
            st.Page("page_1.py", title="Separador de Pedidos por CNPJ", icon=":material/filter_alt:", default=True)
        ]
    }
)

pg.run()
