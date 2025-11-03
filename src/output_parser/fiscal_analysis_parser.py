from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StatusGeral(str, Enum):
    OTIMO = 'otimo'
    BOM = 'bom'
    ATENCAO = 'atencao'
    CRITICO = 'critico'


class Tendencia(str, Enum):
    CRESCIMENTO = 'crescimento'
    ESTAVEL = 'estavel'
    QUEDA = 'queda'


class Complexidade(str, Enum):
    BAIXA = 'baixa'
    MEDIA = 'media'
    ALTA = 'alta'


class NivelRisco(str, Enum):
    BAIXO = 'baixo'
    MEDIO = 'medio'
    ALTO = 'alto'


class TipoAlerta(str, Enum):
    CRITICO = 'critico'
    IMPORTANTE = 'importante'
    INFORMATIVO = 'informativo'


class Prioridade(str, Enum):
    ALTA = 'alta'
    MEDIA = 'media'
    BAIXA = 'baixa'


class PrincipaisMetricas(BaseModel):
    faturamento_total: float = 0.0
    impostos_totais: float = 0.0
    carga_tributaria_efetiva: float = 0.0
    ticket_medio: float = 0.0
    numero_clientes: int = 0
    numero_fornecedores: int = 0


class ResumoExecutivo(BaseModel):
    periodo_analisado: str
    total_notas: int
    principais_metricas: PrincipaisMetricas
    status_geral: StatusGeral
    principais_insights: List[str] = Field(default_factory=list)


class EvolucaoMensal(BaseModel):
    mes: str
    valor: float
    variacao_percentual: float


class Faturamento(BaseModel):
    evolucao_mensal: List[EvolucaoMensal] = Field(default_factory=list)
    tendencia: Tendencia
    previsao_proximo_mes: float = 0.0
    sazonalidade_detectada: bool = False


class ComposicaoCusto(BaseModel):
    categoria: str
    valor: float
    percentual: float


class Custos(BaseModel):
    composicao: List[ComposicaoCusto] = Field(default_factory=list)
    evolucao: str
    oportunidades_reducao: List[str] = Field(default_factory=list)


class ProdutoLucrativo(BaseModel):
    produto: str
    margem: float
    contribuicao: float


class Lucratividade(BaseModel):
    margem_bruta: float = 0.0
    margem_liquida_estimada: float = 0.0
    produtos_mais_lucrativos: List[ProdutoLucrativo] = Field(
        default_factory=list
    )


class AnaliseFinanceira(BaseModel):
    faturamento: Faturamento
    custos: Custos
    lucratividade: Lucratividade


class DistribuicaoImpostos(BaseModel):
    icms: float = 0.0
    ipi: float = 0.0
    pis: float = 0.0
    cofins: float = 0.0


class CargaTributaria(BaseModel):
    total_impostos: float = 0.0
    percentual_sobre_faturamento: float = 0.0
    distribuicao: DistribuicaoImpostos
    comparacao_setor: str


class OportunidadeOtimizacao(BaseModel):
    tipo: str
    descricao: str
    economia_potencial: float
    complexidade: Complexidade


class Compliance(BaseModel):
    score_medio: float = 0.0
    principais_problemas: List[str] = Field(default_factory=list)
    nivel_risco: NivelRisco


class AnaliseTributaria(BaseModel):
    carga_tributaria: CargaTributaria
    oportunidades: List[OportunidadeOtimizacao] = Field(default_factory=list)
    compliance: Compliance


class Fornecedor(BaseModel):
    nome: str
    cnpj: str
    volume_compras: float
    percentual_total: float
    frequencia: int


class ConcentracaoFornecedores(BaseModel):
    indice_concentracao: float
    dependencia_principal: float
    risco: NivelRisco


class AnaliseFornecedores(BaseModel):
    top_fornecedores: List[Fornecedor] = Field(default_factory=list)
    concentracao: ConcentracaoFornecedores
    oportunidades_negociacao: List[str] = Field(default_factory=list)


class ProdutoABC(BaseModel):
    produto: str
    ncm: str
    volume: float
    percentual_faturamento: float


class CurvaABC(BaseModel):
    classe_a: List[ProdutoABC] = Field(default_factory=list)
    classe_b: List[ProdutoABC] = Field(default_factory=list)
    classe_c: List[ProdutoABC] = Field(default_factory=list)


class PerformanceProdutos(BaseModel):
    mais_vendidos: List[str] = Field(default_factory=list)
    maior_margem: List[str] = Field(default_factory=list)
    em_declinio: List[str] = Field(default_factory=list)


class AnaliseProdutos(BaseModel):
    curva_abc: CurvaABC
    performance: PerformanceProdutos


class KPIsFinanceiros(BaseModel):
    roi_estimado: float = 0.0
    ebitda_estimado: float = 0.0
    capital_giro_necessario: float = 0.0
    prazo_medio_recebimento: int = 0
    prazo_medio_pagamento: int = 0


class KPIsOperacionais(BaseModel):
    giro_estoque: float = 0.0
    produtividade: float = 0.0
    eficiencia_fiscal: float = 0.0


class KPIs(BaseModel):
    financeiros: KPIsFinanceiros
    operacionais: KPIsOperacionais


class Alerta(BaseModel):
    tipo: TipoAlerta
    categoria: str
    descricao: str
    impacto: str
    acao_recomendada: str


class Recomendacao(BaseModel):
    prioridade: Prioridade
    area: str
    acao: str
    beneficio_esperado: str
    prazo_implementacao: str
    complexidade: Complexidade


class GraficoSugerido(BaseModel):
    tipo: str
    titulo: str
    descricao: str
    eixo_x: str
    eixo_y: str
    dados_principais: List[str] = Field(default_factory=list)


class MetricaDestaque(BaseModel):
    nome: str
    valor: str
    variacao: str
    status: str


class Dashboards(BaseModel):
    graficos_sugeridos: List[GraficoSugerido] = Field(default_factory=list)
    metricas_destaque: List[MetricaDestaque] = Field(default_factory=list)


class MetadataAnalise(BaseModel):
    data_analise: str
    periodo_dados: str
    total_documentos_analisados: int
    confianca_analise: float = Field(ge=0.0, le=1.0)
    proxima_atualizacao_sugerida: str


class FiscalAnalysisResult(BaseModel):
    """Schema principal para resultado de análise fiscal completa"""

    resumo_executivo: ResumoExecutivo
    analise_financeira: Optional[AnaliseFinanceira] = None
    analise_tributaria: Optional[AnaliseTributaria] = None
    analise_fornecedores: Optional[AnaliseFornecedores] = None
    analise_produtos: Optional[AnaliseProdutos] = None
    kpis: Optional[KPIs] = None
    alertas: List[Alerta] = Field(default_factory=list)
    recomendacoes: List[Recomendacao] = Field(default_factory=list)
    dashboards: Optional[Dashboards] = None
    metadata: MetadataAnalise


class ScoreSaudeFiscal(BaseModel):
    """Score de saúde fiscal da empresa"""

    score_total: float = Field(ge=0.0, le=100.0)
    componentes: dict = Field(default_factory=dict)
    classificacao: str
    principais_pontos_fortes: List[str] = Field(default_factory=list)
    principais_pontos_melhorar: List[str] = Field(default_factory=list)
    evolucao_sugerida: str


class ComparacaoPeriodos(BaseModel):
    """Comparação entre dois períodos"""

    variacao_faturamento_percentual: float
    variacao_faturamento_valor: float
    variacao_carga_tributaria: float
    mudancas_produtos: List[str] = Field(default_factory=list)
    mudancas_fornecedores: List[str] = Field(default_factory=list)
    tendencias_identificadas: List[str] = Field(default_factory=list)
    alertas_deterioracao: List[str] = Field(default_factory=list)
    melhorias_observadas: List[str] = Field(default_factory=list)
