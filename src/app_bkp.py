import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from agents.extraction_agent import FiscalExtractionAgent
from agents.fiscal_intelligence_agent import FiscalIntelligenceAgent


@st.cache_resource
def get_agents():
    fiscal_extraction_agent = FiscalExtractionAgent()
    fiscal_intelligence_agent = FiscalIntelligenceAgent()

    return fiscal_extraction_agent, fiscal_intelligence_agent


fiscal_extraction_agent, fiscal_intelligence_agent = get_agents()


def main():
    st.set_page_config(layout="wide", page_title="🍞 Bread-AI Fiscal")

    st.title("🍞 Bread-AI Fiscal")
    st.subheader("Análise Inteligente de Documentos Fiscais")
    st.divider()

    with st.sidebar:
        st.header("Upload de Documentos")
        st.divider()
        uploaded_files = st.file_uploader(
            "Arraste e solte seus arquivos aqui",
            type=["xml", "pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            st.divider()
            if st.button(
                (
                    "Iniciar Análise Individual"
                    if len(uploaded_files) == 1
                    else "Iniciar Análise em Lote"
                ),
                key="start_analysis_button",
                type="primary",
                width="stretch",
            ):
                st.session_state["analysis"] = perform_analysis(uploaded_files)

    analysis = st.session_state.get("analysis", None)

    if analysis is not None:
        show_files_processed(analysis)

        st.divider()

        print(analysis)
        st.info("Funcionalidades de extração e análise serão implementadas aqui.")

    else:
        st.markdown(
            """
            Bem-vindo ao Bread-AI Fiscal! Esta ferramenta utiliza inteligência artificial
            para extrair, validar e analisar dados de notas fiscais (XML, PDF, Imagem).
            """
        )


def perform_analysis(uploaded_files: list[UploadedFile]) -> dict:
    import json

    # extracted_files = fiscal_extraction_agent.extract_batch(
    #     [file.name for file in uploaded_files]
    # )
    with open("src/test_data/dados_extraidos.json", "r") as f:
        extracted_files = json.load(f)

    extracted_files_success = []
    extracted_files_error = []
    for file in extracted_files:
        if file["status"] == "sucesso":
            extracted_files_success.append(file)
        else:
            extracted_files_error.append(file)

    error = False
    try:
        # business_analysis = fiscal_intelligence_agent.analyze_business(
        #     [file["dados"] for file in extracted_files_success]
        # )
        with open("src/test_data/business_analysis.json", "r") as f:
            business_analysis = json.load(f)

        if "metricas_agregadas" in business_analysis:
            data_quality_report = fiscal_intelligence_agent.get_data_quality_report(
                business_analysis
            )
            summary = fiscal_intelligence_agent.generate_executive_summary(
                business_analysis
            )
        else:
            data_quality_report = None
            summary = None
    except Exception as e:
        business_analysis = None
        data_quality_report = None
        summary = None
        error = True

    # with open("src/test_data/dados_extraidos.json", "w") as f:
    #     json.dump(extracted_files, f, indent=2, ensure_ascii=False)
    # with open("src/test_data/business_analysis.json", "w") as f:
    #     json.dump(business_analysis, f, indent=2, ensure_ascii=False)

    return {
        "processed_files": {
            "success": [arquivo["arquivo"] for arquivo in extracted_files_success],
            "error": [arquivo["arquivo"] for arquivo in extracted_files_success],
            # "error": [arquivo["arquivo"] for arquivo in extracted_files_error],
        },
        "dados_extraidos": extracted_files,
        "business_analysis": business_analysis,
        "data_quality_report": data_quality_report,
        "summary": summary,
        "error": error,
    }


def show_files_processed(analysis: dict):
    with st.expander("📄 Arquivo(s) Processado(s)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="✅ Arquivos Processados com Sucesso",
                value=len(analysis["processed_files"]["success"]),
            )
        with col2:
            st.metric(
                label="❌ Arquivos com Erro",
                value=len(analysis["processed_files"]["error"]),
            )

        n_cols = sum(
            map(
                bool,
                (
                    analysis["processed_files"]["success"],
                    analysis["processed_files"]["error"],
                ),
            )
        )
        if n_cols > 0:
            cols = st.columns(n_cols)
            if analysis["processed_files"]["success"]:
                with cols[0].expander(
                    "✅ Arquivos Processados com Sucesso", expanded=True
                ):
                    for file_name in analysis["processed_files"]["success"]:
                        st.markdown(f"- {file_name}")

            if analysis["processed_files"]["error"]:
                with cols[0 if len(cols) == 1 else 1].expander(
                    "❌ Arquivos com Erro", expanded=True
                ):
                    for file_name in analysis["processed_files"]["error"]:
                        st.markdown(f"- {file_name}")


if __name__ == "__main__":
    main()
