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
    uploaded_file = st.file_uploader(label="", type=["xlsx", "xls", "xlm"], label_visibility="collapsed")

    if uploaded_file:
        df = load_data(uploaded_file)

        @st.dialog(title=f"{uploaded_file.name}", width="medium", icon=":material/visibility:")
        def show_data(dataframe):
            st.dataframe(dataframe, width="stretch", hide_index=True)

        if st.button(f"{uploaded_file.name}", icon=":material/visibility:"):
            show_data(df)

        st.markdown("#### 2. Identifique a coluna dos CNPJs")
        cnpj_col = st.radio(
            label="",
            options=df.columns,
            index=next((i for i, col in enumerate(df.columns) if "cnpj" in col.lower()), None),
            label_visibility="collapsed",
        )

        df[cnpj_col] = df[cnpj_col].apply(lambda cnpj: "".join(filter(str.isalnum, cnpj)))

        if cnpj_col is not None:
            st.markdown("#### 3. Download do pacote de pedidos")

            zip_file = export_zip_file(df, cnpj_col)
            zip_filename = Path(uploaded_file.name).with_suffix(".zip").name

            st.info(
                f"Extraia o conteúdo do arquivo *{zip_filename}* para acessar os {df[cnpj_col].nunique()} pedidos.",
                icon=":material/info:",
            )

            st.download_button(
                label=f"{zip_filename}",
                icon=":material/download:",
                data=zip_file,
                file_name=zip_filename,
                mime="application/zip",
                type="primary",
            )


@st.cache_data(ttl=3600, show_spinner="Processando o arquivo...")
def load_data(uploaded_file):
    try:
        if filetype.guess_extension(uploaded_file) in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file, engine="calamine", dtype=str)

        if filetype.guess_extension(uploaded_file) is None:
            tree = ET.parse(uploaded_file)
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
def export_zip_file(df, cnpj_col):
    try:
        cnpj_list = df[cnpj_col].dropna().unique().tolist()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for cnpj in cnpj_list:
                filtered_df = df[df[cnpj_col] == cnpj]

                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name="Planilha1")

                    worksheet = writer.sheets["Planilha1"]

                    for i, col in enumerate(filtered_df.columns):
                        max_width = max(filtered_df[col].fillna("").astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(i, i, max_width)

                output_filename = "".join(filter(str.isalnum, cnpj)) + ".xlsx"
                zf.writestr(output_filename, excel_buffer.getvalue())

        return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Erro ao gerar o pacote de pedidos: {e}")
        st.stop()


if __name__ == "__main__":
    main()
