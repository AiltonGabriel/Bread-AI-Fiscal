"""
Modelos Pydantic para validação de notas fiscais.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StatusValidacao(str, Enum):
    VALIDO = 'valido'
    INVALIDO = 'invalido'
    COM_AVISOS = 'com_avisos'


class Severidade(str, Enum):
    CRITICO = 'critico'
    ERRO = 'erro'
    AVISO = 'aviso'
    INFO = 'info'


class NivelRisco(str, Enum):
    BAIXO = 'baixo'
    MEDIO = 'medio'
    ALTO = 'alto'
    CRITICO = 'critico'


class ValidacaoDocumento(BaseModel):
    campo: str
    valor: str
    valido: bool
    mensagem: str


class ValidacaoChaveAcesso(BaseModel):
    valida: bool
    estrutura_correta: bool
    digito_verificador_correto: bool
    detalhes: str


class ValidacoesEstruturais(BaseModel):
    documentos: List[ValidacaoDocumento] = Field(default_factory=list)
    codigos_fiscais: List[ValidacaoDocumento] = Field(default_factory=list)
    chave_acesso: Optional[ValidacaoChaveAcesso] = None


class CalculoProduto(BaseModel):
    produto: str
    calculo_correto: bool
    valor_esperado: float
    valor_encontrado: float
    diferenca: float


class CalculoImposto(BaseModel):
    correto: bool
    valor_calculado: float
    valor_declarado: float
    diferenca: float


class CalculosImpostos(BaseModel):
    icms: Optional[CalculoImposto] = None
    ipi: Optional[CalculoImposto] = None
    pis: Optional[CalculoImposto] = None
    cofins: Optional[CalculoImposto] = None


class Totalizadores(BaseModel):
    produtos_correto: bool
    total_nf_correto: bool
    detalhes: str


class ValidacoesMatematicas(BaseModel):
    calculos_produtos: List[CalculoProduto] = Field(default_factory=list)
    calculos_impostos: Optional[CalculosImpostos] = None
    totalizadores: Optional[Totalizadores] = None


class CFOPOperacao(BaseModel):
    compativel: bool
    cfop: str
    tipo_operacao: str
    observacao: Optional[str] = None


class OperacaoInterestadual(BaseModel):
    aplicavel: bool
    aliquota_correta: bool
    difal_calculado: bool
    observacoes: Optional[str] = None


class SubstituicaoTributaria(BaseModel):
    aplicavel: bool
    calculo_correto: bool
    mva_aplicada: Optional[float] = None
    observacoes: Optional[str] = None


class ValidacoesFiscais(BaseModel):
    cfop_operacao: Optional[CFOPOperacao] = None
    operacao_interestadual: Optional[OperacaoInterestadual] = None
    substituicao_tributaria: Optional[SubstituicaoTributaria] = None


class Problema(BaseModel):
    severidade: Severidade
    categoria: str
    campo: str
    descricao: str
    valor_atual: Optional[str] = None
    valor_esperado: Optional[str] = None
    sugestao_correcao: Optional[str] = None
    impacto_fiscal: Optional[str] = None


class AnaliseRisco(BaseModel):
    nivel_risco: NivelRisco
    principais_riscos: List[str] = Field(default_factory=list)
    recomendacoes: List[str] = Field(default_factory=list)
    necessita_revisao_manual: bool = False
    necessita_correcao_urgente: bool = False


class ValidacaoGeral(BaseModel):
    status: StatusValidacao
    score_conformidade: float = Field(ge=0.0, le=100.0)
    total_erros_criticos: int = 0
    total_erros: int = 0
    total_avisos: int = 0
    apto_para_processamento: bool = False


class MetadataValidacao(BaseModel):
    timestamp_validacao: str
    tempo_processamento_ms: Optional[int] = None
    versao_validador: str = '1.0.0'
    regras_aplicadas: Optional[int] = None
    alertas_suprimidos: Optional[int] = None


class NotaFiscalValidation(BaseModel):
    """Schema principal para resultado de validação de Nota Fiscal"""

    validacao_geral: ValidacaoGeral
    validacoes_estruturais: Optional[ValidacoesEstruturais] = Field(
        default_factory=ValidacoesEstruturais
    )
    validacoes_matematicas: Optional[ValidacoesMatematicas] = Field(
        default_factory=ValidacoesMatematicas
    )
    validacoes_fiscais: Optional[ValidacoesFiscais] = Field(
        default_factory=ValidacoesFiscais
    )
    problemas: List[Problema] = Field(default_factory=list)
    analise_risco: AnaliseRisco
    metadata: MetadataValidacao
