from typing import List, Optional

from pydantic import BaseModel, Field


class Endereco(BaseModel):
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None


class Identificacao(BaseModel):
    numero_nf: Optional[str] = None
    serie: Optional[str] = None
    data_emissao: Optional[str] = None
    chave_acesso: Optional[str] = None
    tipo_operacao: Optional[str] = None
    natureza_operacao: Optional[str] = None


class Emitente(BaseModel):
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    endereco: Optional[Endereco] = None


class Destinatario(BaseModel):
    documento: Optional[str] = None
    tipo_documento: Optional[str] = None
    nome: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    endereco: Optional[Endereco] = None


class Impostos(BaseModel):
    icms: Optional[float] = 0.0
    ipi: Optional[float] = 0.0
    pis: Optional[float] = 0.0
    cofins: Optional[float] = 0.0


class Produto(BaseModel):
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    ncm: Optional[str] = None
    cfop: Optional[str] = None
    unidade: Optional[str] = None
    quantidade: Optional[float] = 0.0
    valor_unitario: Optional[float] = 0.0
    valor_total: Optional[float] = 0.0
    impostos: Optional[Impostos] = Field(default_factory=Impostos)


class Totais(BaseModel):
    valor_produtos: Optional[float] = 0.0
    valor_total_nf: Optional[float] = 0.0
    base_calculo_icms: Optional[float] = 0.0
    valor_icms: Optional[float] = 0.0
    base_calculo_icms_st: Optional[float] = 0.0
    valor_icms_st: Optional[float] = 0.0
    valor_ipi: Optional[float] = 0.0
    valor_pis: Optional[float] = 0.0
    valor_cofins: Optional[float] = 0.0
    valor_frete: Optional[float] = 0.0
    valor_seguro: Optional[float] = 0.0
    valor_desconto: Optional[float] = 0.0
    valor_outros: Optional[float] = 0.0


class InformacoesAdicionais(BaseModel):
    informacoes_complementares: Optional[str] = None
    observacoes_fiscais: Optional[str] = None
    forma_pagamento: Optional[str] = None
    transportadora: Optional[str] = None


class Metadata(BaseModel):
    tipo_documento: Optional[str] = None
    formato_original: Optional[str] = None
    confianca_extracao: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    campos_nao_encontrados: Optional[List[str]] = Field(default_factory=list)
    arquivo_processado: Optional[str] = None


class NotaFiscalExtract(BaseModel):
    """Schema principal para extração de dados de Nota Fiscal"""

    identificacao: Identificacao
    emitente: Emitente
    destinatario: Destinatario
    produtos: List[Produto] = Field(default_factory=list)
    totais: Totais
    informacoes_adicionais: Optional[InformacoesAdicionais] = Field(
        default_factory=InformacoesAdicionais
    )
    metadata: Metadata = Field(default_factory=Metadata)
