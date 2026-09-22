import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import filetype
import pandas as pd
import streamlit as st


def main():
    st.set_page_config(
        page_icon="assets/icons/logo_gruposc.png", page_title="Separador de Pedidos por CNPJ", layout="centered"
    )

    with open("assets/styles/style_1.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.title("Separador de Pedidos por CNPJ")
    st.divider()

    st.markdown("#### 1. Faça o upload do arquivo")
    arquivo_upload = st.file_uploader(label="", type=["xlsx", "xls", "xlm"], label_visibility="collapsed")

    if arquivo_upload:
        df = carregar_dados(arquivo_upload)

        if st.button(f"{arquivo_upload.name}", icon=":material/visibility:"):

            @st.dialog(title=f"{arquivo_upload.name}", width="medium", icon=":material/visibility:")
            def exibir_dados(dataframe):
                st.dataframe(dataframe, width="stretch", hide_index=True)

            exibir_dados(df)

        st.markdown("#### 2. Identifique a coluna dos CNPJs")
        coluna_cnpj = st.radio(
            label="",
            options=df.columns,
            index=next((i for i, col in enumerate(df.columns) if "cnpj" in col.lower()), None),
            label_visibility="collapsed",
        )

        df[coluna_cnpj] = df[coluna_cnpj].apply(lambda cnpj: "".join(filter(str.isalnum, cnpj)))

        if coluna_cnpj is not None:
            st.markdown("#### 3. Download do pacote de pedidos")

            arquivo_zip = gerar_arquivo_zip(df, coluna_cnpj)
            nome_arquivo_zip = Path(arquivo_upload.name).with_suffix(".zip").name

            st.info(
                f"Extraia o conteúdo do arquivo *{nome_arquivo_zip}* para acessar os {df[coluna_cnpj].nunique()} pedidos.",
                icon=":material/info:",
            )

            st.download_button(
                label=f"{nome_arquivo_zip}",
                icon=":material/download:",
                data=arquivo_zip,
                file_name=nome_arquivo_zip,
                mime="application/zip",
                type="primary",
            )


@st.cache_data(ttl=3600, show_spinner="Processando o arquivo...")
def carregar_dados(arquivo_upload):
    try:
        if filetype.guess_extension(arquivo_upload) in ["xlsx", "xls"]:
            df = pd.read_excel(arquivo_upload, engine="calamine", dtype=str)

        if filetype.guess_extension(arquivo_upload) is None:
            tree = ET.parse(arquivo_upload)
            root = tree.getroot()

            ns_uri = root.tag.split("}")[0].strip("{")
            ns = {"ss": ns_uri}

            rows = []
            for row in root.findall(".//ss:Row", ns):
                cells = [cell.findtext("ss:Data", "", ns) for cell in row.findall("ss:Cell", ns)]
                if any(cell for cell in cells):
                    rows.append(cells)

            df = pd.DataFrame(rows[1:], columns=rows[0], dtype=str)

        df = df.dropna()

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        st.stop()


@st.cache_data(ttl=3600, show_spinner="Processando o arquivo...")
def gerar_arquivo_zip(df, coluna_cnpj):
    try:
        lista_cnpj = df[coluna_cnpj].dropna().unique().tolist()

        buffer_zip = io.BytesIO()
        with zipfile.ZipFile(buffer_zip, "w") as zf:
            for cnpj in lista_cnpj:
                df_filtrado = df[df[coluna_cnpj] == cnpj]

                buffer_excel = io.BytesIO()
                with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
                    df_filtrado.to_excel(writer, index=False, sheet_name="Planilha1")

                    worksheet = writer.sheets["Planilha1"]

                    for i, col in enumerate(df.columns):
                        largura_max = max(df[col].fillna("").astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(i, i, largura_max)

                arquivo_pedido = "".join(filter(str.isalnum, cnpj)) + ".xlsx"
                zf.writestr(arquivo_pedido, buffer_excel.getvalue())

        return buffer_zip.getvalue()
    except Exception as e:
        st.error(f"Erro ao gerar o pacote de pedidos: {e}")
        st.stop()


if __name__ == "__main__":
    main()
