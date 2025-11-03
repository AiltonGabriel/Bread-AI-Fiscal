import pandas as pd
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

    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False

    def start_processing():
        st.session_state.processing = True
        st.session_state.analysis_done = False

    with st.sidebar:
        st.header("Upload de Documentos")
        st.divider()
        uploaded_files = st.file_uploader(
            "Arraste e solte seus arquivos aqui",
            type=["xml", "pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="file_uploader",
        )
        if uploaded_files:
            st.divider()

            st.button(
                "Iniciar Análise",
                icon="📊",
                key="start_analysis_button",
                type="primary",
                use_container_width=True,
                on_click=start_processing,
                disabled=st.session_state.processing,
            )

    if st.session_state.processing and not st.session_state.analysis_done:
        try:
            with st.spinner("Analisando documentos... Isso pode levar alguns minutos."):
                files_to_process = st.session_state.file_uploader
                if files_to_process:
                    st.session_state.analysis = perform_analysis(files_to_process)
                else:
                    st.session_state.analysis = None
        finally:
            st.session_state.analysis_done = True
            st.session_state.processing = False
            st.rerun()

    analysis = st.session_state.get("analysis", None)

    if analysis is not None:
        show_dashboard(analysis)
    else:
        st.markdown(
            """
            Bem-vindo ao Bread-AI Fiscal! Esta ferramenta utiliza inteligência artificial
            para extrair, validar e analisar dados de notas fiscais (XML, PDF, Imagem).
            
            **Para começar:**
            1. Faça o upload de um ou mais documentos fiscais na barra lateral.
            2. Clique no botão "Iniciar Análise".
            3. Explore os insights gerados pela IA!
            """
        )


def perform_analysis(uploaded_files: list[UploadedFile]) -> dict:

    extracted_files = fiscal_extraction_agent.extract_batch(
        [file.name for file in uploaded_files]
    )

    extracted_files_success = []
    extracted_files_error = []
    for file in extracted_files:
        if file["status"] == "sucesso":
            extracted_files_success.append(file)
        else:
            extracted_files_error.append(file)

    error = False
    try:
        business_analysis = fiscal_intelligence_agent.analyze_business(
            [file["dados"] for file in extracted_files_success]
        )

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

    return {
        "processed_files": {
            "success": [arquivo["arquivo"] for arquivo in extracted_files_success],
            "error": [arquivo["arquivo"] for arquivo in extracted_files_error],
        },
        "dados_extraidos": extracted_files,
        "business_analysis": business_analysis,
        "data_quality_report": data_quality_report,
        "summary": summary,
        "error": error,
    }


def show_dashboard(analysis: dict):
    """
    Displays the main analysis dashboard using expanders.
    """

    show_files_processed(analysis)
    st.divider()

    if not analysis.get("error"):
        show_executive_summary(analysis)
        st.divider()
        show_data_quality_report(analysis)
        st.divider()
        show_business_analysis(analysis)
    else:
        st.error(
            "Ocorreu um erro durante a análise. Não foi possível gerar os relatórios. Por favor, verifique os arquivos ou tente novamente."
        )


def show_files_processed(analysis: dict):
    with st.expander("📄 Arquivo(s) Processado(s)", expanded=True):
        col1, col2 = st.columns(2)
        success_files = analysis.get("processed_files", {}).get("success", [])
        error_files = analysis.get("processed_files", {}).get("error", [])

        with col1:
            st.metric(
                label="✅ Arquivos Processados com Sucesso",
                value=len(success_files),
            )
        with col2:
            st.metric(
                label="❌ Arquivos com Erro",
                value=len(error_files),
            )

        n_cols = sum(map(bool, (success_files, error_files)))
        if n_cols > 0:
            cols = st.columns(n_cols or 1)
            col_idx = 0
            if success_files:
                with cols[col_idx].expander(
                    "✅ Arquivos Processados com Sucesso", expanded=True
                ):
                    for file_name in success_files:
                        st.markdown(f"- {file_name}")
                col_idx += 1
            if error_files:
                with cols[col_idx].expander("❌ Arquivos com Erro", expanded=True):
                    for file_name in error_files:
                        st.markdown(f"- {file_name}")


def show_executive_summary(analysis: dict):
    summary = analysis.get("summary")

    if summary:
        with st.expander("📊 Resumo Executivo", expanded=True):
            st.code(summary, language=None)


def show_data_quality_report(analysis: dict):
    data_quality_report = analysis.get("data_quality_report")

    if data_quality_report:
        with st.expander("🔍 Relatório de Qualidade dos Dados", expanded=True):
            dqr = data_quality_report
            st.subheader(
                f"Classificação Geral: {dqr.get('indicador_visual', '')} {dqr.get('classificacao_geral', 'N/A').title()}"
            )

            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Percentual de Completude",
                f"{dqr.get('percentual_completude', 0):.2f}%",
            )
            col2.metric(
                "Notas Completas", dqr.get("estatisticas", {}).get("notas_completas", 0)
            )
            col3.metric(
                "Notas Incompletas",
                dqr.get("estatisticas", {}).get("notas_incompletas", 0),
            )

            st.write("**Campos com dados ausentes e frequência:**")
            problematic_fields = dqr.get("campos_problematicos", {})
            if problematic_fields:
                st.table(
                    pd.DataFrame(
                        problematic_fields.items(),
                        columns=["Campo", "Nº de Notas Afetadas"],
                    )
                )
            else:
                st.success("Nenhum campo problemático encontrado.")

            st.write("**Recomendações para Melhoria:**")
            for rec in dqr.get("recomendacoes", []):
                st.markdown(f"- {rec}")


def show_business_analysis(analysis: dict):
    business_analysis = analysis.get("business_analysis")

    if business_analysis:
        with st.expander("📈 Dashboard de Análise de Negócio", expanded=True):
            ba = business_analysis

            tabs = st.tabs(
                [
                    "Visão Geral",
                    "Financeiro",
                    "Tributário",
                    "Fornecedores",
                    "Produtos",
                    "Alertas e Recomendações",
                ]
            )

            with tabs[0]:  # Visão Geral
                st.subheader("Principais Métricas Agregadas")
                metrics = ba.get("metricas_agregadas", {}).get("metricas_gerais", {})
                if metrics:
                    c1, c2, c3 = st.columns(3)
                    c1.metric(
                        "Faturamento Total",
                        f"R$ {metrics.get('faturamento_total', 0):,.2f}",
                    )
                    c2.metric(
                        "Ticket Médio", f"R$ {metrics.get('ticket_medio', 0):,.2f}"
                    )
                    c3.metric("Total de Notas", metrics.get("total_notas", 0))
                    c1.metric(
                        "Total de Fornecedores", metrics.get("total_fornecedores", 0)
                    )
                    c2.metric(
                        "Produtos Únicos", metrics.get("total_produtos_unicos", 0)
                    )
                else:
                    st.info("Não foi possível calcular as métricas gerais.")

            with tabs[1]:  # Financeiro
                st.subheader("Análise Financeira")
                financials = ba.get("analise_financeira", {})
                faturamento = financials.get("faturamento", {})
                if (
                    faturamento
                    and "evolucao_mensal" in faturamento
                    and faturamento["evolucao_mensal"]
                ):
                    st.write("**Evolução Mensal do Faturamento**")
                    df_faturamento = pd.DataFrame(faturamento["evolucao_mensal"])
                    df_faturamento = df_faturamento.rename(
                        columns={"mes": "Mês", "valor": "Faturamento (R$)"}
                    )
                    st.bar_chart(df_faturamento.set_index("Mês"), width="stretch")
                else:
                    st.info("Dados de faturamento insuficientes para gerar gráfico.")

            with tabs[2]:  # Tributário
                st.subheader("Análise Tributária")
                tax_analysis = ba.get("analise_tributaria", {})
                tax_load = tax_analysis.get("carga_tributaria", {})
                if tax_load:
                    c1, c2 = st.columns(2)
                    c1.metric(
                        "Total de Impostos",
                        f"R$ {tax_load.get('total_impostos', 0):,.2f}",
                    )
                    c2.metric(
                        "Carga Tributária Efetiva",
                        f"{tax_load.get('percentual_sobre_faturamento', 0):.2f}%",
                    )

                st.write("**Comparativo de Regimes Tributários (Estimativa)**")
                regimes = ba.get("metricas_agregadas", {}).get("comparacao_regimes", {})
                if regimes:
                    processed_regimes = []
                    for name, data in regimes.items():
                        processed_regimes.append(
                            {
                                "Regime": name.replace("_", " ").title(),
                                "Impostos Estimados (R$)": data.get(
                                    "impostos_estimados"
                                )
                                or data.get("impostos_estimados_sem_creditos"),
                                "Alíquota Efetiva (%)": data.get("alíquota_efetiva")
                                or data.get("aliquota_base"),
                                "Observação": data.get("observacao", "-"),
                            }
                        )
                    df_regimes = pd.DataFrame(processed_regimes)
                    st.dataframe(df_regimes, width="stretch", hide_index=True)
                else:
                    st.info(
                        "Não foi possível gerar o comparativo de regimes tributários."
                    )

            with tabs[3]:  # Fornecedores
                st.subheader("Análise de Fornecedores")
                suppliers = ba.get("metricas_agregadas", {}).get("top_fornecedores", [])
                if suppliers:
                    st.write("**Top Fornecedores por Valor**")
                    df_suppliers = pd.DataFrame(suppliers)
                    if len(df_suppliers.columns) == 4:
                        df_suppliers.columns = [
                            "Fornecedor",
                            "Valor Total (R$)",
                            "Qtd. Notas",
                            "% do Faturamento",
                        ]
                    st.dataframe(df_suppliers, width="stretch", hide_index=True)
                else:
                    st.info("Não há dados de fornecedores para exibir.")

            with tabs[4]:  # Produtos
                st.subheader("Análise de Produtos")
                products = ba.get("metricas_agregadas", {}).get("top_produtos", [])
                if products:
                    st.write("**Top Produtos por Valor**")
                    df_products = pd.DataFrame(products)
                    if len(df_products.columns) == 4:
                        df_products.columns = [
                            "Código",
                            "Descrição",
                            "Qtd. Total",
                            "Valor Total (R$)",
                        ]
                    st.dataframe(df_products, width="stretch", hide_index=True)
                else:
                    st.info("Não há dados de produtos para exibir.")

            with tabs[5]:  # Alertas e Recomendações
                st.subheader("Alertas Gerados")
                alerts = ba.get("alertas", [])
                if alerts:
                    for alert in alerts:
                        msg = f"**{alert.get('categoria', 'Alerta')}:** {alert.get('descricao', '')}"
                        if alert.get("tipo") == "critico":
                            st.error(msg, icon="🔥")
                        else:
                            st.warning(msg, icon="⚠️")
                else:
                    st.success("Nenhum alerta gerado.")

                st.divider()
                st.subheader("Recomendações Estratégicas")
                recommendations = ba.get("recomendacoes", [])
                if recommendations:
                    for i, rec in enumerate(recommendations):
                        with st.expander(
                            f"**{rec.get('prioridade', 'N/A').title()}:** {rec.get('area', 'Recomendação')} - {rec.get('acao', '')[:50]}..."
                        ):
                            st.markdown(f"**Ação:** {rec.get('acao')}")
                            st.markdown(
                                f"**Benefício Esperado:** {rec.get('beneficio_esperado')}"
                            )
                            st.markdown(
                                f"**Complexidade:** {rec.get('complexidade', 'N/A').title()}"
                            )
                            st.markdown(
                                f"**Prazo Sugerido:** {rec.get('prazo_implementacao', 'N/A')}"
                            )
                else:
                    st.success("Nenhuma recomendação gerada.")


if __name__ == "__main__":
    main()
