import json
import logging
from datetime import datetime
from typing import Dict, List

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.google import Gemini
from dotenv import load_dotenv

from fiscal_calculator import FiscalCalculator
from output_parser.fiscal_analysis_parser import FiscalAnalysisResult
from output_parser.fiscal_validation_parser import NotaFiscalValidation

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FiscalIntelligenceAgent:
    """
    Agente unificado de inteligência fiscal.
    Realiza cálculos determinísticos e envia contexto enriquecido para o LLM.
    """

    def __init__(self):
        """Inicializa o agente de inteligência fiscal"""
        self.calculator = FiscalCalculator()
        self.analysis_cache = {}
        logger.info("FiscalIntelligenceAgent inicializado")

    def _create_validation_agent(self) -> Agent:
        """Cria agente para validação contextual"""
        return Agent(
            name="Fiscal Context Validator",
            model=Gemini(id="gemini-2.0-flash"),
            db=InMemoryDb(),
            markdown=True,
            instructions=self._get_validation_instructions(),
            output_schema=NotaFiscalValidation,
            add_history_to_context=False,
        )

    def _create_analysis_agent(self) -> Agent:
        """Cria agente para análise de negócio"""
        return Agent(
            name="Fiscal Business Analyst",
            model=Gemini(id="gemini-2.0-flash"),
            db=InMemoryDb(),
            markdown=True,
            instructions=self._get_analysis_instructions(),
            output_schema=FiscalAnalysisResult,
            add_history_to_context=True,
        )

    def validate_context(self, invoice_data: Dict, deterministic_results: Dict) -> Dict:
        """
        Valida contexto fiscal de UMA nota específica.
        """
        logger.info(
            f"Validando contexto da nota {invoice_data.get('identificacao', {}).get('numero_nf', 'N/A')}"
        )

        start_time = datetime.now()

        metricas_calculadas = self.calculator.analisar_nota_individual(invoice_data)

        qualidade = metricas_calculadas.get("qualidade_dados", {})
        if qualidade.get("campos_none_lista"):
            logger.warning(
                f"Nota possui campos ausentes (None): {qualidade.get('campos_none_lista')}"
            )

        agent = self._create_validation_agent()

        prompt = self._build_validation_prompt(
            invoice_data, deterministic_results, metricas_calculadas
        )

        try:
            response = agent.run(prompt, stream=False)

            if isinstance(response.content, NotaFiscalValidation):
                result = response.content.model_dump()
            elif hasattr(response, "content"):
                if isinstance(response.content, str):
                    result = json.loads(response.content)
                else:
                    result = response.content
            else:
                result = {"raw_response": str(response)}

            if isinstance(result, dict):
                result["metricas_calculadas"] = metricas_calculadas

                if "metadata" not in result:
                    result["metadata"] = {}

                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                result["metadata"]["timestamp_validacao"] = datetime.now().isoformat()
                result["metadata"]["tempo_processamento_ms"] = int(processing_time)
                result["metadata"]["tipo_analise"] = "validacao_contextual"

            logger.info(f"Validação contextual concluída em {processing_time:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Erro na validação contextual: {e}")
            raise

    def _get_validation_instructions(self) -> str:
        """Instruções para validação contextual"""
        return """
        Você é um especialista em VALIDAÇÃO CONTEXTUAL de notas fiscais brasileiras.
        
        ⚠️ IMPORTANTE: Todos os cálculos matemáticos JÁ FORAM REALIZADOS!
        Você receberá métricas pré-calculadas e validações determinísticas concluídas.
        
        ⚠️ ATENÇÃO: Alguns campos podem estar ausentes (None) nas notas fiscais.
        Quando isso ocorrer, os cálculos foram feitos considerando R$ 0,00 para esses campos.
        Sempre mencione nas recomendações quando houver campos ausentes.
        
        ## SEU PAPEL: Análise Contextual e Estratégica
        
        ### 1. INTERPRETAÇÃO DE OPORTUNIDADES FISCAIS:
        
        Você receberá cálculos de:
        - Créditos recuperáveis (valores já calculados em R$)
        - Comparação entre regimes tributários (já computada)
        - Diferenças de ICMS (já identificadas)
        - Alertas sobre campos ausentes (None)
        
        Sua função é:
        - INTERPRETAR o que esses números significam
        - CONSIDERAR que campos None podem indicar dados incompletos
        - ALERTAR se falta informação crítica (ex: PIS/COFINS ausentes)
        - PRIORIZAR as ações por impacto
        - SUGERIR próximos passos práticos
        - ESTIMAR complexidade e prazo de implementação
        - CONTEXTUALIZAR para o tipo de negócio
        
        ### 2. ANÁLISE DE QUALIDADE DOS DADOS:
        
        Se houver campos ausentes:
        - Identifique QUAIS campos estão faltando
        - Avalie o IMPACTO da falta desses dados
        - Sugira COMO obter essas informações
        - Estime QUANTO pode estar sendo perdido
        
        ### 3. ANÁLISE DE RISCO CONTEXTUAL:
        
        Avalie:
        - Esta operação pode chamar atenção fiscal?
        - Há padrões atípicos nos códigos/valores?
        - Os CFOPs estão adequados ao contexto?
        - Operações interestaduais estão corretas?
        - Há inconsistências entre descrição e classificação?
        - Dados ausentes podem esconder irregularidades?
        
        Classifique: BAIXO / MÉDIO / ALTO / CRÍTICO
        
        ### 4. RECOMENDAÇÕES PRÁTICAS (3-5 ações):
        
        Para cada recomendação:
        - Ação específica (ex: "Solicitar crédito de R$ X.XXX,XX referente a PIS/COFINS não aproveitados")
        - Prioridade (alta/média/baixa)
        - Benefício (use os valores JÁ CALCULADOS)
        - Prazo (imediato/curto/médio/longo)
        - Complexidade (baixa/média/alta)
        - Próximos passos claros
        - SE houver campos None: mencione necessidade de completar dados
        
        ### 5. ALERTAS INTELIGENTES:
        
        Identifique:
        - Campos ausentes que impedem análise completa
        - Inconsistências que podem gerar autuação
        - Prazos fiscais relevantes
        - Mudanças legislativas recentes aplicáveis
        - Documentos/informações faltando
        
        ## DIRETRIZES CRÍTICAS:
        
        ✅ USE os valores JÁ CALCULADOS nas seções de métricas
        ✅ INTERPRETE e CONTEXTUALIZE os números
        ✅ ALERTE sobre campos ausentes e seu impacto
        ✅ Seja ESPECÍFICO nas recomendações
        ✅ PRIORIZE por impacto financeiro real
        ✅ Use linguagem CLARA para não-especialistas
        
        ❌ NÃO refaça cálculos (já foram feitos)
        ❌ NÃO invente valores (use os fornecidos)
        ❌ NÃO ignore campos ausentes
        ❌ NÃO seja genérico nas recomendações
        ❌ NÃO use jargão técnico sem explicar
        
        Você é um CONSULTOR FISCAL INTELIGENTE focado em INTERPRETAÇÃO e ESTRATÉGIA!
        """

    def _build_validation_prompt(
        self,
        invoice_data: Dict,
        deterministic_results: Dict,
        metricas_calculadas: Dict,
    ) -> str:
        """Constrói prompt com dados enriquecidos"""
        val_summary = deterministic_results.get("validacao_geral", {})
        problemas = deterministic_results.get("problemas", [])

        identificacao = invoice_data.get("identificacao", {})
        emitente = invoice_data.get("emitente", {})
        destinatario = invoice_data.get("destinatario", {})
        totais = invoice_data.get("totais", {})

        problemas_text = "✅ Nenhum problema encontrado"
        if problemas:
            problemas_text = "\n".join(
                [
                    f"  • [{p.get('severity', 'N/A').upper()}] {p.get('field', 'N/A')}: {p.get('description', 'N/A')}"
                    for p in problemas[:5]
                ]
            )

        carga = metricas_calculadas.get("carga_tributaria", {})
        oportunidades = metricas_calculadas.get("oportunidades_creditos", {})
        regimes = metricas_calculadas.get("comparacao_regimes", {})
        icms_analise = metricas_calculadas.get("analise_icms", {})
        qualidade_dados = metricas_calculadas.get("qualidade_dados", {})

        alertas_dados = ""
        if qualidade_dados.get("campos_none_lista"):
            alertas_dados = f"""
        ⚠️ ALERTA DE DADOS AUSENTES:
        - Campos com valor None: {', '.join(qualidade_dados.get('campos_none_lista', []))}
        - Integridade dos dados: {qualidade_dados.get('integridade_dados', 'N/A').upper()}
        - Impacto: Cálculos de oportunidades podem estar SUBESTIMADOS
        - Observação: {oportunidades.get('observacao', 'N/A')}
        """

        return f"""
        Realize uma ANÁLISE CONTEXTUAL desta nota fiscal usando as métricas PRÉ-CALCULADAS abaixo:
        
        ## RESUMO DA OPERAÇÃO:
        - Número: {identificacao.get('numero_nf', 'N/A')}
        - Tipo: {identificacao.get('tipo_operacao', 'N/A')}
        - Data: {identificacao.get('data_emissao', 'N/A')}
        - Emitente: {emitente.get('razao_social', 'N/A')} (UF: {emitente.get('endereco', {}).get('uf', 'N/A')})
        - Destinatário: {destinatario.get('nome', 'N/A')} (UF: {destinatario.get('endereco', {}).get('uf', 'N/A')})
        - Valor Total: R$ {totais.get('valor_total_nf', 0):,.2f}
        {alertas_dados}
        
        ## MÉTRICAS FISCAIS JÁ CALCULADAS:
        
        ### Carga Tributária:
        - Percentual: {carga.get('percentual', 0):.2f}%
        - Classificação: {carga.get('classificacao', 'N/A')}
        - Total Impostos: R$ {metricas_calculadas.get('impostos_calculados', {}).get('total_impostos', 0):,.2f}
        - Campos ausentes: {', '.join(metricas_calculadas.get('impostos_calculados', {}).get('campos_ausentes', [])) or 'Nenhum'}
        
        ### Oportunidades de Créditos (PRÉ-CALCULADAS):
        - PIS recuperável: R$ {oportunidades.get('pis', {}).get('recuperavel', 0):,.2f} {'⚠️ (AUSENTE NA NOTA)' if oportunidades.get('pis', {}).get('ausente') else ''}
        - COFINS recuperável: R$ {oportunidades.get('cofins', {}).get('recuperavel', 0):,.2f} {'⚠️ (AUSENTE NA NOTA)' if oportunidades.get('cofins', {}).get('ausente') else ''}
        - **TOTAL RECUPERÁVEL MENSAL: R$ {oportunidades.get('total_recuperavel_mensal', 0):,.2f}**
        - **TOTAL RECUPERÁVEL ANUAL: R$ {oportunidades.get('total_recuperavel_anual', 0):,.2f}**
        - Observação: {oportunidades.get('observacao', 'Todos os campos presentes')}
        
        ### Análise ICMS:
        - Valor cobrado: R$ {icms_analise.get('valor_cobrado', 0):,.2f} {'⚠️ (AUSENTE NA NOTA)' if icms_analise.get('ausente') else ''}
        - Valor esperado: R$ {icms_analise.get('valor_esperado', 0):,.2f}
        - Diferença: R$ {icms_analise.get('diferenca', 0):,.2f}
        - Status: {icms_analise.get('status', 'N/A').upper()}
        
        ### Comparação de Regimes (PRÉ-CALCULADA):
        - Simples Nacional: R$ {regimes.get('simples_nacional', {}).get('impostos_estimados', 0):,.2f} ({regimes.get('simples_nacional', {}).get('aliquota_efetiva', 0):.1f}%)
        - Lucro Presumido: R$ {regimes.get('lucro_presumido', {}).get('impostos_estimados', 0):,.2f} ({regimes.get('lucro_presumido', {}).get('aliquota_efetiva', 0):.2f}%)
        - Lucro Real (sem créditos): R$ {regimes.get('lucro_real', {}).get('impostos_estimados_sem_creditos', 0):,.2f}
        
        ## VALIDAÇÃO DETERMINÍSTICA:
        - Status: {val_summary.get('status', 'N/A').upper()}
        - Score: {val_summary.get('score_conformidade', 0):.1f}/100
        - Problemas: {problemas_text}
        
        ---
        
        Com base nos CÁLCULOS PRÉ-REALIZADOS acima, forneça:
        
        1. **ANÁLISE DE QUALIDADE DOS DADOS**:
           {f"- Há {len(qualidade_dados.get('campos_none_lista', []))} campo(s) ausente(s): {', '.join(qualidade_dados.get('campos_none_lista', []))}" if qualidade_dados.get('campos_none_lista') else "- Dados completos"}
           - Qual o impacto dos dados ausentes?
           - Como obter essas informações?
           - Quanto pode estar sendo perdido?
        
        2. **INTERPRETAÇÃO DAS OPORTUNIDADES**:
           - O que significa o crédito recuperável de R$ {oportunidades.get('total_recuperavel_anual', 0):,.2f}/ano?
           - Este valor pode estar SUBESTIMADO devido a campos ausentes?
           - Vale a pena mudar de regime? Qual o melhor?
           - Priorize ações por ROI
        
        3. **ANÁLISE DE RISCO**:
           - Nível de risco desta operação (baixo/médio/alto/crítico)
           - Justificativa baseada no contexto
           - O que pode chamar atenção fiscal?
           - Dados ausentes aumentam o risco?
        
        4. **CONFORMIDADE CONTEXTUAL**:
           - Códigos fiscais adequados?
           - Alíquotas típicas para este tipo de operação?
           - Documentação adicional necessária?
        
        5. **RECOMENDAÇÕES** (3-5 ações priorizadas):
           Use os VALORES JÁ CALCULADOS para quantificar benefícios.
           PRIORIZE completar dados ausentes se houver.
           Exemplo: "1. URGENTE: Obter valores de PIS/COFINS (pode haver R$ XXX não contabilizados)"
        
        6. **ALERTAS**:
           - Dados críticos ausentes?
           - Há algo incomum?
           - Prazos importantes?
           - Documentos faltando?
        
        LEMBRE-SE: 
        - Todos os valores monetários JÁ ESTÃO CALCULADOS. Use-os!
        - Campos None foram tratados como R$ 0,00 nos cálculos
        - SEMPRE mencione quando houver dados ausentes e seu impacto
        """

    def analyze_business(self, invoices_data: List[Dict]) -> Dict:
        """
        Analisa múltiplas notas fiscais para gerar insights de negócio.
        """
        logger.info(f"Analisando {len(invoices_data)} notas fiscais")

        start_time = datetime.now()

        metricas_agregadas = self.calculator.analisar_multiplas_notas(invoices_data)

        qualidade = metricas_agregadas.get("qualidade_dados", {})
        if qualidade.get("notas_com_campos_none", 0) > 0:
            logger.warning(
                f"{qualidade.get('notas_com_campos_none')} de {len(invoices_data)} notas possuem campos ausentes (None)"
            )

        agent = self._create_analysis_agent()

        prompt = self._build_analysis_prompt(metricas_agregadas)

        try:
            response = agent.run(prompt, stream=False)

            if isinstance(response.content, FiscalAnalysisResult):
                result = response.content.model_dump()
            elif hasattr(response, "content"):
                if isinstance(response.content, str):
                    result = json.loads(response.content)
                else:
                    result = response.content
            else:
                result = {"raw_response": str(response)}

            if isinstance(result, dict):
                result["metricas_agregadas"] = metricas_agregadas

                if "metadata" not in result:
                    result["metadata"] = {}

                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                result["metadata"]["data_analise"] = datetime.now().isoformat()
                result["metadata"]["total_documentos_analisados"] = len(invoices_data)
                result["metadata"]["tempo_processamento_ms"] = int(processing_time)

            logger.info(f"Análise de negócio concluída em {processing_time:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Erro na análise de negócio: {e}")
            raise

    def _get_analysis_instructions(self) -> str:
        """Instruções para análise de negócio"""
        return """
        Você é um analista fiscal especialista em INTELIGÊNCIA DE NEGÓCIOS.
        
        ⚠️ TODOS OS CÁLCULOS E AGREGAÇÕES JÁ FORAM REALIZADOS!
        Você receberá métricas agregadas pré-calculadas de múltiplas notas fiscais.
        
        ⚠️ ATENÇÃO: Algumas notas podem ter campos ausentes (None).
        Isso pode impactar a precisão das análises. Sempre mencione a qualidade dos dados.
        
        ## SEU PAPEL: Interpretação Estratégica e Insights de Negócio
        
        ### 1. ANÁLISE DE QUALIDADE DOS DADOS:
        
        PRIMEIRO, avalie:
        - Quantas notas têm campos ausentes?
        - Quais campos estão faltando com mais frequência?
        - Qual o impacto na confiabilidade da análise?
        - Recomendações para melhorar qualidade dos dados
        
        ### 2. ANÁLISE FINANCEIRA:
        
        Com ressalvas sobre qualidade dos dados, interprete:
        - Tendências (crescimento, queda, sazonalidade)
        - Padrões relevantes
        - Previsões (com nível de confiança)
        - Ações baseadas nos dados disponíveis
        
        ### 3. ANÁLISE TRIBUTÁRIA:
        
        Considerando dados ausentes:
        - Carga tributária pode estar SUBESTIMADA?
        - Qual regime é mais vantajoso?
        - Economia potencial (valores mínimos se houver None)
        - Ações tributárias priorizadas
        
        ### 4. RECOMENDAÇÕES (5-10 ações prioritárias):
        
        SEMPRE inclua:
        - Se >20% notas têm campos None: PRIORIDADE MÁXIMA = melhorar qualidade dados
        - Outras ações com ressalvas sobre confiabilidade
        - Benefícios potenciais (mínimos/máximos se houver incerteza)
        
        ## DIRETRIZES CRÍTICAS:
        
        ✅ USE as métricas PRÉ-CALCULADAS fornecidas
        ✅ SEMPRE mencione qualidade dos dados
        ✅ INDIQUE nível de confiança das conclusões
        ✅ QUANTIFIQUE com valores calculados
        ✅ PRIORIZE melhorar qualidade de dados se necessário
        
        ❌ NÃO recalcule totais/somas (já feito)
        ❌ NÃO ignore dados ausentes
        ❌ NÃO faça conclusões categóricas com dados incompletos
        ❌ NÃO invente números
        
        Você é um ESTRATEGISTA FISCAL focado em INSIGHTS CONFIÁVEIS!
        """

    def _build_analysis_prompt(self, metricas_agregadas: Dict) -> str:
        """Constrói prompt para análise de negócio"""
        metricas = metricas_agregadas.get("metricas_gerais", {})
        impostos = metricas_agregadas.get("impostos_agregados", {})
        carga = metricas_agregadas.get("carga_tributaria_agregada", {})
        top_fornecedores = metricas_agregadas.get("top_fornecedores", [])
        concentracao = metricas_agregadas.get("analise_concentracao", {})
        top_produtos = metricas_agregadas.get("top_produtos", [])
        regimes = metricas_agregadas.get("comparacao_regimes", {})
        evolucao = metricas_agregadas.get("evolucao_temporal", [])
        qualidade = metricas_agregadas.get("qualidade_dados", {})

        alerta_qualidade = ""
        if qualidade.get("notas_com_campos_none", 0) > 0:
            alerta_qualidade = f"""
        ⚠️ ALERTA DE QUALIDADE DOS DADOS:
        - {qualidade.get('notas_com_campos_none', 0)} de {metricas.get('total_notas', 0)} notas ({qualidade.get('percentual_notas_incompletas', 0):.1f}%) possuem campos ausentes
        - Campos ausentes por tipo: {json.dumps(qualidade.get('campos_none_por_tipo', {}), ensure_ascii=False)}
        - Impacto: Valores de impostos e oportunidades podem estar SUBESTIMADOS
        - Observação: {qualidade.get('observacao', 'N/A')}
        """

        return f"""
        Realize uma ANÁLISE ESTRATÉGICA usando as métricas PRÉ-CALCULADAS abaixo:
        {alerta_qualidade}
        
        ## MÉTRICAS GERAIS (JÁ CALCULADAS):
        - Total de notas: {metricas.get('total_notas', 0)}
        - Faturamento total: R$ {metricas.get('faturamento_total', 0):,.2f}
        - Ticket médio: R$ {metricas.get('ticket_medio', 0):,.2f}
        - Total fornecedores: {metricas.get('total_fornecedores', 0)}
        - Produtos únicos: {metricas.get('total_produtos_unicos', 0)}
        
        ## IMPOSTOS AGREGADOS (JÁ CALCULADOS):
        - ICMS: R$ {impostos.get('icms_total', 0):,.2f} ({carga.get('distribuicao', {}).get('icms_percent', 0):.1f}%)
        - PIS: R$ {impostos.get('pis_total', 0):,.2f} ({carga.get('distribuicao', {}).get('pis_percent', 0):.1f}%) {'⚠️ PODE ESTAR SUBESTIMADO' if qualidade.get('campos_none_por_tipo', {}).get('PIS', 0) > 0 else ''}
        - COFINS: R$ {impostos.get('cofins_total', 0):,.2f} ({carga.get('distribuicao', {}).get('cofins_percent', 0):.1f}%) {'⚠️ PODE ESTAR SUBESTIMADO' if qualidade.get('campos_none_por_tipo', {}).get('COFINS', 0) > 0 else ''}
        - **TOTAL IMPOSTOS: R$ {impostos.get('total_impostos', 0):,.2f}**
        
        ## CARGA TRIBUTÁRIA (JÁ CALCULADA):
        - Percentual: {carga.get('percentual', 0):.2f}%
        - Classificação: {carga.get('classificacao', 'N/A')}
        - Observação: {'Valores podem estar subestimados devido a campos ausentes' if qualidade.get('notas_com_campos_none', 0) > 0 else 'Dados completos'}
        
        ## TOP 5 FORNECEDORES (JÁ RANQUEADOS):
        {self._format_top_list(top_fornecedores[:5], 'fornecedor')}
        
        ## ANÁLISE DE CONCENTRAÇÃO (JÁ CALCULADA):
        - Concentração Top 3: {concentracao.get('concentracao_top3_percent', 0):.1f}%
        - Nível de risco: {concentracao.get('nivel_risco', 'N/A').upper()}
        
        ## TOP 5 PRODUTOS (JÁ RANQUEADOS):
        {self._format_top_list(top_produtos[:5], 'produto')}
        
        ## COMPARAÇÃO DE REGIMES (JÁ CALCULADA):
        - Simples Nacional: R$ {regimes.get('simples_nacional', {}).get('impostos_estimados', 0):,.2f}
        - Lucro Presumido: R$ {regimes.get('lucro_presumido', {}).get('impostos_estimados', 0):,.2f}
        - Lucro Real: R$ {regimes.get('lucro_real', {}).get('impostos_estimados_sem_creditos', 0):,.2f}
        
        ## EVOLUÇÃO TEMPORAL (JÁ CALCULADA):
        {self._format_evolucao(evolucao)}
        
        ## QUALIDADE DOS DADOS:
        - Integridade: {qualidade.get('percentual_notas_incompletas', 0):.1f}% das notas têm campos ausentes
        - Confiabilidade da análise: {'BAIXA' if qualidade.get('percentual_notas_incompletas', 0) > 50 else 'MÉDIA' if qualidade.get('percentual_notas_incompletas', 0) > 20 else 'ALTA'}
        
        ---
        
        Com base nessas MÉTRICAS PRÉ-CALCULADAS, forneça:
        
        1. **ANÁLISE DE QUALIDADE DOS DADOS** (CRÍTICO):
           - Qual o impacto de {qualidade.get('percentual_notas_incompletas', 0):.1f}% das notas terem dados ausentes?
           - Quais conclusões são confiáveis e quais são especulativas?
           - Como melhorar a qualidade dos dados?
           - Qual o custo estimado dos dados ausentes?
        
        2. **ANÁLISE FINANCEIRA**:
           - Qual a tendência de faturamento? (use dados de evolução temporal)
           - Há sazonalidade?
           - Previsão para próximo período (com nível de confiança)
           - Ações para aumentar faturamento
        
        3. **ANÁLISE TRIBUTÁRIA**:
           - A carga de {carga.get('percentual', 0):.2f}% está adequada? (considere possível subestimação)
           - Qual regime é mais vantajoso? (use comparação já calculada)
           - Economia potencial anual? (valores mínimos se houver dados ausentes)
           - Prioridades tributárias
        
        4. **ANÁLISE DE FORNECEDORES**:
           - Concentração de {concentracao.get('concentracao_top3_percent', 0):.1f}% é arriscada?
           - Oportunidades de negociação
           - Necessidade de diversificação
        
        5. **ANÁLISE DE PRODUTOS**:
           - Curva ABC interpretada
           - Produtos estratégicos
           - Recomendações de mix
        
        6. **KPIs DERIVADOS** (calcule apenas estes):
           - ROI estimado
           - Eficiência fiscal (quanto % do faturamento vai para impostos vs média do setor)
           - Velocidade de crescimento
           - Nível de confiança em cada KPI (baseado em qualidade dos dados)
        
        7. **ALERTAS CRÍTICOS**:
           - Se >20% notas têm dados ausentes: ALERTA MÁXIMO sobre qualidade
           - Riscos identificados
           - Oportunidades urgentes
           - Ações imediatas necessárias
        
        8. **RECOMENDAÇÕES** (5-10 ações priorizadas):
           {'PRIORIDADE 1: Implementar processo para capturar campos ausentes (PIS, COFINS, etc.)' if qualidade.get('percentual_notas_incompletas', 0) > 20 else ''}
           Use os VALORES JÁ CALCULADOS para quantificar benefícios
           Indique nível de confiança de cada recomendação
           Priorize por impacto financeiro
        
        IMPORTANTE: 
        - USE os valores fornecidos. NÃO recalcule totais!
        - SEMPRE mencione quando valores podem estar subestimados
        - INDIQUE nível de confiança das conclusões
        - SE >20% dados ausentes: priorize MELHORAR QUALIDADE DOS DADOS
        """

    def _format_top_list(self, items: List[Dict], tipo: str) -> str:
        """Formata lista top para prompt"""
        if not items:
            return "Nenhum item disponível"

        resultado = []
        for i, item in enumerate(items, 1):
            if tipo == "fornecedor":
                resultado.append(
                    f"  {i}. {item.get('nome', 'N/A')}: "
                    f"R$ {item.get('valor_total', 0):,.2f} "
                    f"({item.get('percentual_faturamento', 0):.1f}% do total)"
                )
            else:
                resultado.append(
                    f"  {i}. {item.get('descricao', 'N/A')}: "
                    f"R$ {item.get('valor_total', 0):,.2f} "
                    f"(Qtd: {item.get('quantidade_total', 0):.0f})"
                )
        return "\n".join(resultado)

    def _format_evolucao(self, evolucao: List[Dict]) -> str:
        """Formata evolução temporal"""
        if not evolucao:
            return "Sem dados de evolução"

        resultado = []
        for item in evolucao[-6:]:
            resultado.append(
                f"  • {item.get('mes', 'N/A')}: "
                f"{item.get('quantidade_notas', 0)} notas, "
                f"R$ {item.get('faturamento', 0):,.2f}"
            )
        return "\n".join(resultado)

    def generate_executive_summary(self, analysis_result: Dict) -> str:
        """Gera resumo executivo em texto."""
        resumo = analysis_result.get("resumo_executivo", {})
        metricas_agg = analysis_result.get("metricas_agregadas", {})
        metricas = metricas_agg.get("metricas_gerais", {})
        impostos = metricas_agg.get("impostos_agregados", {})
        carga = metricas_agg.get("carga_tributaria_agregada", {})
        qualidade = metricas_agg.get("qualidade_dados", {})

        alerta_qualidade = ""
        if qualidade.get("percentual_notas_incompletas", 0) > 20:
            alerta_qualidade = f"""
        ⚠️  ALERTA: {qualidade.get('percentual_notas_incompletas', 0):.1f}% das notas possuem dados ausentes
            Valores podem estar SUBESTIMADOS!
        """

        summary = f"""
        ╔═══════════════════════════════════════════════════════════════╗
        ║              RESUMO EXECUTIVO FISCAL                          ║
        ╚═══════════════════════════════════════════════════════════════╝
        {alerta_qualidade}
        📄 NOTAS ANALISADAS: {metricas.get('total_notas', 0)}
        
        💰 INDICADORES PRINCIPAIS:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        • Faturamento Total: R$ {metricas.get('faturamento_total', 0):,.2f}
        • Impostos Totais: R$ {impostos.get('total_impostos', 0):,.2f}
        • Carga Tributária: {carga.get('percentual', 0):.1f}% ({carga.get('classificacao', 'N/A')})
        • Ticket Médio: R$ {metricas.get('ticket_medio', 0):,.2f}
        • Fornecedores: {metricas.get('total_fornecedores', 0)}
        
        📊 QUALIDADE DOS DADOS:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        • Notas com dados completos: {metricas.get('total_notas', 0) - qualidade.get('notas_com_campos_none', 0)}
        • Notas com campos ausentes: {qualidade.get('notas_com_campos_none', 0)}
        • {qualidade.get('observacao', 'N/A')}
        
        🎯 STATUS GERAL: {resumo.get('status_geral', 'ANALISADO').upper()}
        """

        return summary

    def get_data_quality_report(self, analysis_result: Dict) -> Dict:
        """
        Gera relatório detalhado de qualidade dos dados.

        Args:
            analysis_result: Resultado da análise

        Returns:
            Dict com relatório de qualidade
        """
        metricas_agg = analysis_result.get("metricas_agregadas", {})
        qualidade = metricas_agg.get("qualidade_dados", {})

        total_notas = metricas_agg.get("metricas_gerais", {}).get("total_notas", 0)
        notas_completas = total_notas - qualidade.get("notas_com_campos_none", 0)

        percentual_incompleto = qualidade.get("percentual_notas_incompletas", 0)
        if percentual_incompleto == 0:
            classificacao = "excelente"
            cor = "🟢"
        elif percentual_incompleto < 10:
            classificacao = "boa"
            cor = "🟢"
        elif percentual_incompleto < 30:
            classificacao = "aceitável"
            cor = "🟡"
        elif percentual_incompleto < 50:
            classificacao = "ruim"
            cor = "🟠"
        else:
            classificacao = "crítica"
            cor = "🔴"

        return {
            "classificacao_geral": classificacao,
            "indicador_visual": cor,
            "percentual_completude": 100 - percentual_incompleto,
            "estatisticas": {
                "total_notas": total_notas,
                "notas_completas": notas_completas,
                "notas_incompletas": qualidade.get("notas_com_campos_none", 0),
                "percentual_incompleto": percentual_incompleto,
            },
            "campos_problematicos": qualidade.get("campos_none_por_tipo", {}),
            "impacto_estimado": self._estimar_impacto_dados_ausentes(
                qualidade, metricas_agg
            ),
            "recomendacoes": self._gerar_recomendacoes_qualidade(
                qualidade, percentual_incompleto
            ),
        }

    def _estimar_impacto_dados_ausentes(
        self, qualidade: Dict, metricas_agg: Dict
    ) -> Dict:
        """Estima impacto financeiro de dados ausentes"""
        campos_none = qualidade.get("campos_none_por_tipo", {})
        metricas_gerais = metricas_agg.get("metricas_gerais", {})
        faturamento_total = metricas_gerais.get("faturamento_total", 0)
        total_notas = metricas_gerais.get("total_notas", 1)

        impacto_pis = 0
        impacto_cofins = 0

        if campos_none.get("PIS", 0) > 0 and total_notas > 0:
            proporcao_sem_pis = campos_none.get("PIS", 0) / total_notas
            impacto_pis = faturamento_total * proporcao_sem_pis * 0.0165

        if campos_none.get("COFINS", 0) > 0 and total_notas > 0:
            proporcao_sem_cofins = campos_none.get("COFINS", 0) / total_notas
            impacto_cofins = faturamento_total * proporcao_sem_cofins * 0.076

        impacto_total = impacto_pis + impacto_cofins

        return {
            "pis_nao_contabilizado_estimado": float(impacto_pis),
            "cofins_nao_contabilizado_estimado": float(impacto_cofins),
            "total_estimado_ausente": float(impacto_total),
            "impacto_anual_estimado": float(impacto_total * 12),
            "detalhamento": {
                "notas_sem_pis": campos_none.get("PIS", 0),
                "notas_sem_cofins": campos_none.get("COFINS", 0),
                "total_notas": total_notas,
                "proporcao_pis": (
                    f"{(campos_none.get('PIS', 0) / total_notas * 100):.1f}%"
                    if total_notas > 0
                    else "0%"
                ),
                "proporcao_cofins": (
                    f"{(campos_none.get('COFINS', 0) / total_notas * 100):.1f}%"
                    if total_notas > 0
                    else "0%"
                ),
            },
            "observacao": "Valores estimados com base em alíquotas médias aplicadas proporcionalmente ao faturamento das notas com dados ausentes",
        }

    def _gerar_recomendacoes_qualidade(
        self, qualidade: Dict, percentual_incompleto: float
    ) -> List[str]:
        """Gera recomendações para melhorar qualidade dos dados"""
        recomendacoes = []
        campos_none = qualidade.get("campos_none_por_tipo", {})

        if percentual_incompleto > 50:
            recomendacoes.append(
                "URGENTE: Implementar processo de validação de dados na captura das notas fiscais"
            )
        elif percentual_incompleto > 20:
            recomendacoes.append(
                "Implementar verificação de completude dos dados fiscais"
            )

        if campos_none.get("PIS", 0) > 0:
            recomendacoes.append(
                f"Corrigir captura de PIS ({campos_none.get('PIS', 0)} notas afetadas)"
            )

        if campos_none.get("COFINS", 0) > 0:
            recomendacoes.append(
                f"Corrigir captura de COFINS ({campos_none.get('COFINS', 0)} notas afetadas)"
            )

        if campos_none.get("ICMS", 0) > 0:
            recomendacoes.append(
                f"Verificar extração de ICMS ({campos_none.get('ICMS', 0)} notas afetadas)"
            )

        if percentual_incompleto > 0:
            recomendacoes.append("Revisar processo de extração de dados (OCR/XML)")
            recomendacoes.append(
                "Implementar alertas automáticos para campos críticos ausentes"
            )

        if not recomendacoes:
            recomendacoes.append("Manter processo atual de captura de dados")

        return recomendacoes


if __name__ == "__main__":
    from fiscal_validator import FiscalValidator

    exemplo_nf_com_none = {
        "identificacao": {
            "numero_nf": "000.011.334",
            "serie": "001",
            "data_emissao": "2025-05-09",
            "chave_acesso": "3525.0531.1525.6200.0346.5500.1000.0113.3410.0044.0803",
            "tipo_operacao": "0 - Entrada",
            "natureza_operacao": "021 VENDA OFICINA - PECAS",
        },
        "emitente": {
            "cnpj": "31.152.562/0003-46",
            "razao_social": "NOBRE COMERCIO DE MOTOCICLETAS",
            "inscricao_estadual": "254228535117",
            "endereco": {
                "logradouro": "RUA RIO BRANCO, 889",
                "bairro": "CARAGUATATUBA",
                "cidade": "CARAGUATATUBA",
                "uf": "SP",
                "cep": "11665600",
            },
        },
        "destinatario": {
            "documento": "529.278.128-29",
            "tipo_documento": "CPF",
            "nome": "JOAO VITOR",
            "endereco": {
                "logradouro": "RUA MARIA MADALENA 814",
                "bairro": "TAQUARAL",
                "cidade": "Ubatuba",
                "uf": "SP",
                "cep": "11.695-700",
            },
        },
        "produtos": [
            {
                "codigo": "90793AB42600",
                "descricao": "OLEO YAMALUBE 4T",
                "ncm": "27101932",
                "cfop": "5656",
                "unidade": "4",
                "quantidade": 1.0,
                "valor_unitario": 32.9,
                "valor_total": 32.9,
                "impostos": {
                    "icms": 0.0,
                    "ipi": 0.0,
                    "pis": None,  # ⚠️ None
                    "cofins": None,  # ⚠️ None
                },
            },
            {
                "codigo": "904301222700",
                "descricao": "GAXETA",
                "ncm": "73182900",
                "cfop": "5102",
                "unidade": "4",
                "quantidade": 1.0,
                "valor_unitario": 1.94,
                "valor_total": 1.94,
                "impostos": {
                    "icms": 0.35,
                    "ipi": 0.0,
                    "pis": None,  # ⚠️ None
                    "cofins": None,  # ⚠️ None
                },
            },
        ],
        "totais": {
            "valor_produtos": 259.78,
            "valor_total_nf": 259.78,
            "base_calculo_icms": 15.1,
            "valor_icms": 2.72,
            "base_calculo_icms_st": 0.0,
            "valor_icms_st": 0.0,
            "valor_ipi": 0.0,
            "valor_pis": None,  # ⚠️ None
            "valor_cofins": None,  # ⚠️ None
            "valor_frete": 0.0,
            "valor_seguro": 0.0,
            "valor_desconto": 0.0,
            "valor_outros": 0.0,
        },
        "informacoes_adicionais": {
            "informacoes_complementares": "Nota com campos ausentes para teste",
        },
        "metadata": {
            "tipo_documento": "NF-e",
            "formato_original": "pdf",
        },
    }

    print("=" * 70)
    print("🔬 TESTE COMPLETO DO FISCAL INTELLIGENCE AGENT COM None")
    print("=" * 70)

    # 1. Validação determinística
    print("\n1️⃣  VALIDAÇÃO DETERMINÍSTICA...")
    validator = FiscalValidator()
    val_results = validator.validate_invoice(exemplo_nf_com_none)
    print(f"   Status: {val_results['validacao_geral']['status']}")
    print(f"   Score: {val_results['validacao_geral']['score_conformidade']:.1f}/100")

    # 2. Criar agente
    print("\n2️⃣  Criando agente...")
    agent = FiscalIntelligenceAgent()

    # 3. Testar análise calculadora (sem LLM)
    print("\n3️⃣  Analisando nota com valores None (calculadora)...")
    metricas = agent.calculator.analisar_nota_individual(exemplo_nf_com_none)

    print(f"\n📊 Métricas Calculadas:")
    print(
        f"   • Total Impostos: R$ {metricas['impostos_calculados']['total_impostos']:,.2f}"
    )
    print(f"   • Carga Tributária: {metricas['carga_tributaria']['percentual']:.2f}%")
    print(f"   • Campos Ausentes: {metricas['impostos_calculados']['campos_ausentes']}")
    print(
        f"   • Crédito Recuperável Anual: R$ {metricas['oportunidades_creditos']['total_recuperavel_anual']:,.2f}"
    )

    qualidade = metricas.get("qualidade_dados", {})
    print(f"\n📋 Qualidade dos Dados:")
    print(f"   • Integridade: {qualidade.get('integridade_dados', 'N/A').upper()}")
    print(f"   • Campos None: {qualidade.get('campos_none_total', 0)}")
    print(f"   • Lista: {qualidade.get('campos_none_lista', [])}")

    # 4. Validação contextual COM LLM (nota individual)
    print("\n4️⃣  VALIDAÇÃO CONTEXTUAL COM LLM (nota individual)...")
    try:
        context_result = agent.validate_context(exemplo_nf_com_none, val_results)
        print(f"   ✅ Análise contextual concluída")
        print(f"   📄 Campos no resultado: {list(context_result.keys())}")

        # Mostra qualidade dos dados detectada
        if "metricas_calculadas" in context_result:
            qual = context_result["metricas_calculadas"].get("qualidade_dados", {})
            print(
                f"   ⚠️  Campos ausentes detectados: {qual.get('campos_none_lista', [])}"
            )
    except Exception as e:
        print(f"   ❌ Erro na validação contextual: {e}")

    # 5. Análise múltiplas notas (calculadora)
    print("\n5️⃣  Analisando múltiplas notas (calculadora)...")
    metricas_agg = agent.calculator.analisar_multiplas_notas([exemplo_nf_com_none] * 3)

    qualidade_agg = metricas_agg.get("qualidade_dados", {})
    print(f"\n📊 Qualidade Agregada:")
    print(f"   • {qualidade_agg.get('observacao', 'N/A')}")
    print(
        f"   • Percentual Incompleto: {qualidade_agg.get('percentual_notas_incompletas', 0):.1f}%"
    )
    print(f"   • Campos None por Tipo: {qualidade_agg.get('campos_none_por_tipo', {})}")

    # 6. Análise de negócio COM LLM (múltiplas notas)
    print("\n6️⃣  ANÁLISE DE NEGÓCIO COM LLM (múltiplas notas)...")
    try:
        business_result = agent.analyze_business([exemplo_nf_com_none] * 3)
        breakpoint()
        print(f"   ✅ Análise de negócio concluída")
        print(f"   📄 Campos no resultado: {list(business_result.keys())}")

        # Mostra qualidade detectada
        if "metricas_agregadas" in business_result:
            qual_agg = business_result["metricas_agregadas"].get("qualidade_dados", {})
            print(f"   ⚠️  {qual_agg.get('observacao', 'N/A')}")
            print(
                f"   📊 Percentual incompleto: {qual_agg.get('percentual_notas_incompletas', 0):.1f}%"
            )
    except Exception as e:
        print(f"   ❌ Erro na análise de negócio: {e}")

    # 7. Relatório de qualidade
    print("\n7️⃣  Gerando relatório de qualidade...")
    if "metricas_agregadas" in business_result:
        relatorio = agent.get_data_quality_report(business_result)

        print(
            f"\n{relatorio['indicador_visual']} CLASSIFICAÇÃO: {relatorio['classificacao_geral'].upper()}"
        )
        print(f"   • Completude: {relatorio['percentual_completude']:.1f}%")
        print(
            f"   • Impacto Estimado: R$ {relatorio['impacto_estimado']['impacto_anual_estimado']:,.2f}/ano"
        )
        print(f"\n   📋 Recomendações:")
        for i, rec in enumerate(relatorio["recomendacoes"][:5], 1):
            print(f"      {i}. {rec}")

    # 8. Resumo executivo
    print("\n8️⃣  RESUMO EXECUTIVO:")
    if "metricas_agregadas" in business_result:
        summary = agent.generate_executive_summary(business_result)
        print(summary)

    print("\n" + "=" * 70)
    print("✅ TESTE COMPLETO CONCLUÍDO!")
    print("   • Calculadora: Tratamento robusto de None ✓")
    print("   • Validação contextual (LLM): Alerta sobre dados ausentes ✓")
    print("   • Análise de negócio (LLM): Considera qualidade dos dados ✓")
    print("   • Relatórios: Quantifica impacto de dados ausentes ✓")
    print("=" * 70)
