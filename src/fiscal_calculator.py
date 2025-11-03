import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Dict, List, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FiscalCalculator:
    """
    Calculadora fiscal determinística com tratamento robusto de None.
    Realiza todos os cálculos necessários ANTES de enviar para o LLM.
    """

    def __init__(self):
        self.tax_rates = {
            'pis_padrao': Decimal('1.65'),
            'cofins_padrao': Decimal('7.6'),
            'pis_cumulativo': Decimal('0.65'),
            'cofins_cumulativo': Decimal('3.0'),
            'icms_interno': {
                'SP': Decimal('18.0'),
                'RJ': Decimal('20.0'),
                'MG': Decimal('18.0'),
                'PR': Decimal('19.5'),
                'SC': Decimal('17.0'),
                'RS': Decimal('17.0'),
                'default': Decimal('18.0'),
            },
        }

    def _safe_decimal(
        self, value: Union[int, float, str, None], default: float = 0.0
    ) -> Decimal:
        """
        Converte valor para Decimal com segurança, tratando None e valores inválidos.

        Args:
            value: Valor a converter
            default: Valor padrão se conversão falhar

        Returns:
            Decimal convertido ou default
        """
        if value is None:
            return Decimal(str(default))

        try:
            # Remove espaços e vírgulas se for string
            if isinstance(value, str):
                value = value.strip().replace(',', '.')

            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.warning(
                f"Erro ao converter '{value}' para Decimal: {e}. Usando default {default}"
            )
            return Decimal(str(default))

    def _safe_get(self, dictionary: Dict, *keys, default=None):
        """
        Acessa chaves aninhadas com segurança.

        Args:
            dictionary: Dicionário a acessar
            *keys: Sequência de chaves
            default: Valor padrão se não encontrar

        Returns:
            Valor encontrado ou default
        """
        result = dictionary
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, default)
            else:
                return default
        return result if result is not None else default

    def analisar_nota_individual(self, invoice_data: Dict) -> Dict:
        """
        Calcula todas as métricas fiscais de uma nota individual.
        Trata robustamente valores None e ausentes.
        """
        totais = invoice_data.get('totais', {})
        produtos = invoice_data.get('produtos', [])
        emitente_uf = self._safe_get(
            invoice_data, 'emitente', 'endereco', 'uf', default='SP'
        )
        destinatario_uf = self._safe_get(
            invoice_data, 'destinatario', 'endereco', 'uf', default='SP'
        )

        # Valores base com tratamento de None
        valor_total = self._safe_decimal(totais.get('valor_total_nf'))
        valor_icms = self._safe_decimal(totais.get('valor_icms'))
        valor_pis = self._safe_decimal(totais.get('valor_pis'))
        valor_cofins = self._safe_decimal(totais.get('valor_cofins'))
        valor_ipi = self._safe_decimal(totais.get('valor_ipi'))

        # Contar campos com None para alertas
        campos_none = []
        if totais.get('valor_pis') is None:
            campos_none.append('PIS')
        if totais.get('valor_cofins') is None:
            campos_none.append('COFINS')
        if totais.get('valor_icms') is None:
            campos_none.append('ICMS')

        # 1. CÁLCULO DE IMPOSTOS TOTAIS
        total_impostos = (
            valor_icms + valor_pis + valor_cofins + valor_ipi
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # 2. CARGA TRIBUTÁRIA
        carga_tributaria = (
            (total_impostos / valor_total * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if valor_total > 0
            else Decimal('0')
        )

        # 3. ANÁLISE DE CRÉDITOS RECUPERÁVEIS (PIS/COFINS não cumulativo)
        credito_pis_potencial = (
            valor_total * self.tax_rates['pis_padrao'] / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        credito_cofins_potencial = (
            valor_total * self.tax_rates['cofins_padrao'] / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        credito_pis_recuperavel = max(
            Decimal('0'), credito_pis_potencial - valor_pis
        )
        credito_cofins_recuperavel = max(
            Decimal('0'), credito_cofins_potencial - valor_cofins
        )
        credito_total_recuperavel = (
            credito_pis_recuperavel + credito_cofins_recuperavel
        )

        # 4. ANÁLISE ICMS
        aliquota_icms_uf = self.tax_rates['icms_interno'].get(
            emitente_uf, self.tax_rates['icms_interno']['default']
        )
        base_icms = self._safe_decimal(totais.get('base_calculo_icms'))
        icms_esperado = (
            (base_icms * aliquota_icms_uf / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if base_icms > 0
            else Decimal('0')
        )

        diferenca_icms = valor_icms - icms_esperado

        # 5. COMPARAÇÃO DE REGIMES TRIBUTÁRIOS
        comparacao_regimes = self._comparar_regimes_tributarios(
            float(valor_total)
        )

        # 6. ANÁLISE POR PRODUTO
        analise_produtos = self._analisar_produtos(produtos)

        # 7. OPERAÇÃO INTERESTADUAL
        operacao_interestadual = emitente_uf != destinatario_uf

        return {
            'impostos_calculados': {
                'icms': float(valor_icms),
                'pis': float(valor_pis),
                'cofins': float(valor_cofins),
                'ipi': float(valor_ipi),
                'total_impostos': float(total_impostos),
                'campos_ausentes': campos_none,  # Alerta sobre campos None
            },
            'carga_tributaria': {
                'percentual': float(carga_tributaria),
                'classificacao': self._classificar_carga_tributaria(
                    float(carga_tributaria)
                ),
                'valor_total_nf': float(valor_total),
            },
            'oportunidades_creditos': {
                'pis': {
                    'atual': float(valor_pis),
                    'potencial': float(credito_pis_potencial),
                    'recuperavel': float(credito_pis_recuperavel),
                    'ausente': totais.get('valor_pis') is None,
                },
                'cofins': {
                    'atual': float(valor_cofins),
                    'potencial': float(credito_cofins_potencial),
                    'recuperavel': float(credito_cofins_recuperavel),
                    'ausente': totais.get('valor_cofins') is None,
                },
                'total_recuperavel_mensal': float(credito_total_recuperavel),
                'total_recuperavel_anual': float(
                    credito_total_recuperavel * Decimal('12')
                ),
                'observacao': 'Valores calculados considerando campos ausentes como R$ 0,00'
                if campos_none
                else None,
            },
            'analise_icms': {
                'valor_cobrado': float(valor_icms),
                'valor_esperado': float(icms_esperado),
                'diferenca': float(diferenca_icms),
                'aliquota_uf': float(aliquota_icms_uf),
                'base_calculo': float(base_icms),
                'status': 'correto'
                if abs(diferenca_icms) < Decimal('0.50')
                else 'verificar',
                'ausente': totais.get('valor_icms') is None,
            },
            'comparacao_regimes': comparacao_regimes,
            'analise_produtos': analise_produtos,
            'contexto_operacao': {
                'interestadual': operacao_interestadual,
                'uf_emitente': emitente_uf,
                'uf_destinatario': destinatario_uf,
                'total_produtos': len(produtos),
            },
            'qualidade_dados': {
                'campos_none_total': len(campos_none),
                'campos_none_lista': campos_none,
                'integridade_dados': 'completa'
                if not campos_none
                else 'parcial',
            },
        }

    def analisar_multiplas_notas(self, invoices_data: List[Dict]) -> Dict:
        """
        Calcula métricas agregadas de múltiplas notas.
        Trata robustamente valores None e ausentes.
        """
        if not invoices_data:
            return {}

        # Agregações
        total_notas = len(invoices_data)
        faturamento_total = Decimal('0')
        impostos_total = Decimal('0')
        icms_total = Decimal('0')
        pis_total = Decimal('0')
        cofins_total = Decimal('0')
        ipi_total = Decimal('0')

        fornecedores = {}
        produtos_dict = {}
        notas_por_mes = {}
        notas_com_none = 0
        campos_none_contador = {'PIS': 0, 'COFINS': 0, 'ICMS': 0, 'IPI': 0}

        for inv in invoices_data:
            totais = inv.get('totais', {})

            # Faturamento
            valor_nf = self._safe_decimal(totais.get('valor_total_nf'))
            faturamento_total += valor_nf

            # Impostos com tratamento de None
            icms = self._safe_decimal(totais.get('valor_icms'))
            pis = self._safe_decimal(totais.get('valor_pis'))
            cofins = self._safe_decimal(totais.get('valor_cofins'))
            ipi = self._safe_decimal(totais.get('valor_ipi'))

            # Contar Nones
            nota_tem_none = False
            if totais.get('valor_pis') is None:
                campos_none_contador['PIS'] += 1
                nota_tem_none = True
            if totais.get('valor_cofins') is None:
                campos_none_contador['COFINS'] += 1
                nota_tem_none = True
            if totais.get('valor_icms') is None:
                campos_none_contador['ICMS'] += 1
                nota_tem_none = True
            if totais.get('valor_ipi') is None:
                campos_none_contador['IPI'] += 1
                nota_tem_none = True

            if nota_tem_none:
                notas_com_none += 1

            icms_total += icms
            pis_total += pis
            cofins_total += cofins
            ipi_total += ipi
            impostos_total += icms + pis + cofins + ipi

            # Fornecedores
            emitente = self._safe_get(
                inv, 'emitente', 'razao_social', default='N/A'
            )
            if emitente not in fornecedores:
                fornecedores[emitente] = {
                    'valor': Decimal('0'),
                    'quantidade': 0,
                }
            fornecedores[emitente]['valor'] += valor_nf
            fornecedores[emitente]['quantidade'] += 1

            # Produtos
            for prod in inv.get('produtos', []):
                codigo = prod.get('codigo', 'N/A')
                if codigo not in produtos_dict:
                    produtos_dict[codigo] = {
                        'descricao': prod.get('descricao', 'N/A'),
                        'quantidade': Decimal('0'),
                        'valor_total': Decimal('0'),
                    }
                produtos_dict[codigo]['quantidade'] += self._safe_decimal(
                    prod.get('quantidade')
                )
                produtos_dict[codigo]['valor_total'] += self._safe_decimal(
                    prod.get('valor_total')
                )

            # Distribuição mensal
            data_emissao = self._safe_get(
                inv, 'identificacao', 'data_emissao', default=''
            )
            if data_emissao:
                mes = data_emissao[:7]  # YYYY-MM
                if mes not in notas_por_mes:
                    notas_por_mes[mes] = {
                        'quantidade': 0,
                        'valor': Decimal('0'),
                    }
                notas_por_mes[mes]['quantidade'] += 1
                notas_por_mes[mes]['valor'] += valor_nf

        # Cálculos finais
        carga_tributaria = (
            (impostos_total / faturamento_total * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if faturamento_total > 0
            else Decimal('0')
        )

        ticket_medio = (
            (faturamento_total / Decimal(str(total_notas))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if total_notas > 0
            else Decimal('0')
        )

        # Top fornecedores
        top_fornecedores = sorted(
            [
                {
                    'nome': nome,
                    'valor_total': float(dados['valor']),
                    'quantidade_notas': dados['quantidade'],
                    'percentual_faturamento': float(
                        (
                            dados['valor'] / faturamento_total * Decimal('100')
                        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    if faturamento_total > 0
                    else 0,
                }
                for nome, dados in fornecedores.items()
            ],
            key=lambda x: x['valor_total'],
            reverse=True,
        )[:10]

        # Top produtos
        top_produtos = sorted(
            [
                {
                    'codigo': codigo,
                    'descricao': dados['descricao'],
                    'quantidade_total': float(dados['quantidade']),
                    'valor_total': float(dados['valor_total']),
                }
                for codigo, dados in produtos_dict.items()
            ],
            key=lambda x: x['valor_total'],
            reverse=True,
        )[:10]

        # Análise de concentração
        concentracao_top3 = sum(
            f['percentual_faturamento'] for f in top_fornecedores[:3]
        )

        # Comparação de regimes
        comparacao_regimes = self._comparar_regimes_tributarios(
            float(faturamento_total)
        )

        # Evolução temporal
        evolucao_mensal = [
            {
                'mes': mes,
                'quantidade_notas': dados['quantidade'],
                'faturamento': float(dados['valor']),
            }
            for mes, dados in sorted(notas_por_mes.items())
        ]

        return {
            'metricas_gerais': {
                'total_notas': total_notas,
                'faturamento_total': float(faturamento_total),
                'ticket_medio': float(ticket_medio),
                'total_fornecedores': len(fornecedores),
                'total_produtos_unicos': len(produtos_dict),
            },
            'impostos_agregados': {
                'icms_total': float(icms_total),
                'pis_total': float(pis_total),
                'cofins_total': float(cofins_total),
                'ipi_total': float(ipi_total),
                'total_impostos': float(impostos_total),
            },
            'carga_tributaria_agregada': {
                'percentual': float(carga_tributaria),
                'classificacao': self._classificar_carga_tributaria(
                    float(carga_tributaria)
                ),
                'distribuicao': {
                    'icms_percent': float(
                        (
                            icms_total / impostos_total * Decimal('100')
                        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    if impostos_total > 0
                    else 0,
                    'pis_percent': float(
                        (pis_total / impostos_total * Decimal('100')).quantize(
                            Decimal('0.01'), rounding=ROUND_HALF_UP
                        )
                    )
                    if impostos_total > 0
                    else 0,
                    'cofins_percent': float(
                        (
                            cofins_total / impostos_total * Decimal('100')
                        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    if impostos_total > 0
                    else 0,
                },
            },
            'top_fornecedores': top_fornecedores,
            'analise_concentracao': {
                'concentracao_top3_percent': float(concentracao_top3),
                'nivel_risco': 'alto'
                if concentracao_top3 > 70
                else 'medio'
                if concentracao_top3 > 50
                else 'baixo',
            },
            'top_produtos': top_produtos,
            'comparacao_regimes': comparacao_regimes,
            'evolucao_temporal': evolucao_mensal,
            'qualidade_dados': {
                'notas_com_campos_none': notas_com_none,
                'percentual_notas_incompletas': float(
                    (
                        Decimal(str(notas_com_none))
                        / Decimal(str(total_notas))
                        * Decimal('100')
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                )
                if total_notas > 0
                else 0,
                'campos_none_por_tipo': campos_none_contador,
                'observacao': f'{notas_com_none} de {total_notas} notas possuem campos ausentes (None)'
                if notas_com_none > 0
                else 'Todos os campos preenchidos',
            },
        }

    def _comparar_regimes_tributarios(self, faturamento_mensal: float) -> Dict:
        """Compara regimes tributários."""
        fat = self._safe_decimal(faturamento_mensal)

        # Simples Nacional (estimativa)
        impostos_simples = (fat * Decimal('10.0') / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # Lucro Presumido
        impostos_presumido = (fat * Decimal('3.65') / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # Lucro Real (sem créditos, estimativa conservadora)
        impostos_real = (fat * Decimal('9.25') / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        return {
            'simples_nacional': {
                'impostos_estimados': float(impostos_simples),
                'aliquota_efetiva': 10.0,
            },
            'lucro_presumido': {
                'impostos_estimados': float(impostos_presumido),
                'aliquota_efetiva': 3.65,
            },
            'lucro_real': {
                'impostos_estimados_sem_creditos': float(impostos_real),
                'aliquota_base': 9.25,
                'observacao': 'Valor pode ser menor com aproveitamento de créditos',
            },
        }

    def _analisar_produtos(self, produtos: List[Dict]) -> Dict:
        """Analisa produtos de uma nota."""
        if not produtos:
            return {}

        valor_total = Decimal('0')
        produtos_sem_icms = []
        produtos_sem_pis_cofins = []

        for prod in produtos:
            valor = self._safe_decimal(prod.get('valor_total'))
            valor_total += valor

            impostos = prod.get('impostos', {})
            icms_val = impostos.get('icms')

            # Verifica None explicitamente
            if icms_val is None or icms_val == 0:
                produtos_sem_icms.append(prod.get('descricao', 'N/A'))

            if impostos.get('pis') is None or impostos.get('cofins') is None:
                produtos_sem_pis_cofins.append(prod.get('descricao', 'N/A'))

        return {
            'total_produtos': len(produtos),
            'valor_medio_produto': float(
                (valor_total / Decimal(str(len(produtos)))).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            )
            if produtos
            else 0,
            'produtos_sem_icms': {
                'quantidade': len(produtos_sem_icms),
                'exemplos': produtos_sem_icms[:3],
            },
            'produtos_sem_pis_cofins': {
                'quantidade': len(produtos_sem_pis_cofins),
                'exemplos': produtos_sem_pis_cofins[:3],
            },
        }

    def _classificar_carga_tributaria(self, percentual: float) -> str:
        """Classifica carga tributária."""
        if percentual < 10:
            return 'Baixa'
        elif percentual < 20:
            return 'Moderada'
        elif percentual < 30:
            return 'Alta'
        else:
            return 'Muito Alta'
