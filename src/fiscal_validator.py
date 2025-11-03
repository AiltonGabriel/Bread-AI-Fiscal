import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationError:
    """Representa um erro de validação"""

    def __init__(
        self,
        severity: str,
        category: str,
        field: str,
        description: str,
        current_value: Optional[str] = None,
        expected_value: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        self.severity = severity
        self.category = category
        self.field = field
        self.description = description
        self.current_value = current_value
        self.expected_value = expected_value
        self.suggestion = suggestion

    def to_dict(self) -> Dict:
        return {
            'severity': self.severity,
            'category': self.category,
            'field': self.field,
            'description': self.description,
            'current_value': self.current_value,
            'expected_value': self.expected_value,
            'suggestion': self.suggestion,
        }


class FiscalValidator:
    """
    Validador determinístico para notas fiscais brasileiras.
    Realiza validações matemáticas, de formato e regras fiscais fixas.
    """

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

        self.tax_rates = {
            'pis_padrao': 1.65,
            'cofins_padrao': 7.6,
            'pis_cumulativo': 0.65,
            'cofins_cumulativo': 3.0,
            'icms_interno': {
                'PR': 19.5,
                'SC': 17.0,
                'RS': 17.0,
                'SP': 18.0,
                'RJ': 20.0,
                'MG': 18.0,
                'ES': 17.0,
                'AC': 19.0,
                'AM': 20.0,
                'AP': 18.0,
                'PA': 19.0,
                'RO': 19.5,
                'RR': 20.0,
                'TO': 20.0,
                'AL': 19.0,
                'BA': 20.5,
                'CE': 20.0,
                'MA': 23.0,
                'PB': 20.0,
                'PE': 20.5,
                'PI': 22.5,
                'RN': 20.0,
                'SE': 18.0,
                'DF': 20.0,
                'GO': 19.0,
                'MT': 17.0,
                'MS': 17.0,
                'default': 18.0,
            },
            'icms_interestadual': {'sul_sudeste': 12.0, 'outras_regioes': 7.0},
        }

        self.regioes = {
            'sul_sudeste': ['PR', 'SC', 'RS', 'SP', 'RJ', 'MG'],
            'outras_regioes': [
                'AC',
                'AM',
                'AP',
                'PA',
                'RO',
                'RR',
                'TO',
                'AL',
                'BA',
                'CE',
                'MA',
                'PB',
                'PE',
                'PI',
                'RN',
                'SE',
                'DF',
                'GO',
                'MT',
                'MS',
                'ES',
            ],
        }

        logger.info(
            'FiscalValidator inicializado com alíquotas atualizadas 2024-2025'
        )

    def validate_cnpj(self, cnpj: str) -> Tuple[bool, str]:
        """
        Valida CNPJ usando algoritmo oficial brasileiro.

        Args:
            cnpj: CNPJ para validar (com ou sem formatação)

        Returns:
            Tupla (válido, mensagem)
        """
        cnpj_clean = re.sub(r'[^0-9]', '', cnpj)

        if len(cnpj_clean) != 14:
            return (
                False,
                f'CNPJ deve ter 14 dígitos (encontrado: {len(cnpj_clean)})',
            )

        if cnpj_clean in [d * 14 for d in '0123456789']:
            return False, 'CNPJ com todos os dígitos iguais é inválido'

        sum_1 = 0
        weight_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        for i in range(12):
            sum_1 += int(cnpj_clean[i]) * weight_1[i]

        remainder_1 = sum_1 % 11
        digit_1 = 0 if remainder_1 < 2 else 11 - remainder_1

        if int(cnpj_clean[12]) != digit_1:
            return False, 'Primeiro dígito verificador inválido'

        sum_2 = 0
        weight_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        for i in range(13):
            sum_2 += int(cnpj_clean[i]) * weight_2[i]

        remainder_2 = sum_2 % 11
        digit_2 = 0 if remainder_2 < 2 else 11 - remainder_2

        if int(cnpj_clean[13]) != digit_2:
            return False, 'Segundo dígito verificador inválido'

        return True, 'CNPJ válido'

    def validate_cpf(self, cpf: str) -> Tuple[bool, str]:
        """
        Valida CPF usando algoritmo oficial brasileiro.

        Args:
            cpf: CPF para validar (com ou sem formatação)

        Returns:
            Tupla (válido, mensagem)
        """
        cpf_clean = re.sub(r'[^0-9]', '', cpf)

        if len(cpf_clean) != 11:
            return (
                False,
                f'CPF deve ter 11 dígitos (encontrado: {len(cpf_clean)})',
            )

        if cpf_clean in [d * 11 for d in '0123456789']:
            return False, 'CPF com todos os dígitos iguais é inválido'

        sum_1 = sum(int(cpf_clean[i]) * (10 - i) for i in range(9))
        remainder_1 = sum_1 % 11
        digit_1 = 0 if remainder_1 < 2 else 11 - remainder_1

        if int(cpf_clean[9]) != digit_1:
            return False, 'Primeiro dígito verificador inválido'

        sum_2 = sum(int(cpf_clean[i]) * (11 - i) for i in range(10))
        remainder_2 = sum_2 % 11
        digit_2 = 0 if remainder_2 < 2 else 11 - remainder_2

        if int(cpf_clean[10]) != digit_2:
            return False, 'Segundo dígito verificador inválido'

        return True, 'CPF válido'

    def validate_chave_acesso(self, chave: str) -> Tuple[bool, str, Dict]:
        """
        Valida chave de acesso da NF-e (44 dígitos).

        Estrutura: UF(2) + AAMM(4) + CNPJ(14) + Modelo(2) + Série(3) +
                   Número(9) + Tipo(1) + Código(8) + DV(1) = 44 dígitos

        Args:
            chave: Chave de acesso

        Returns:
            Tupla (válido, mensagem, detalhes)
        """
        chave_clean = re.sub(r'[^0-9]', '', chave)

        if len(chave_clean) != 44:
            return (
                False,
                f'Chave deve ter 44 dígitos (encontrado: {len(chave_clean)})',
                {},
            )

        details = {
            'uf': chave_clean[0:2],
            'ano_mes': chave_clean[2:6],
            'cnpj': chave_clean[6:20],
            'modelo': chave_clean[20:22],
            'serie': chave_clean[22:25],
            'numero': chave_clean[25:34],
            'tipo_emissao': chave_clean[34:35],
            'codigo': chave_clean[35:43],
            'dv': chave_clean[43:44],
        }

        weights = list(range(2, 10)) * 5 + [2, 3, 4]
        sum_calc = sum(
            int(chave_clean[i]) * weights[42 - i] for i in range(43)
        )

        remainder = sum_calc % 11
        expected_dv = 0 if remainder in [0, 1] else 11 - remainder

        if int(details['dv']) != expected_dv:
            return (
                False,
                f'Dígito verificador inválido (esperado: {expected_dv})',
                details,
            )

        return True, 'Chave de acesso válida', details

    def validate_ncm(self, ncm: str) -> Tuple[bool, str]:
        """
        Valida código NCM (8 dígitos numéricos).

        Args:
            ncm: Código NCM

        Returns:
            Tupla (válido, mensagem)
        """
        ncm_clean = re.sub(r'[^0-9]', '', ncm) if ncm else ''

        if len(ncm_clean) != 8:
            return (
                False,
                f'NCM deve ter 8 dígitos (encontrado: {len(ncm_clean)})',
            )

        return True, 'NCM válido'

    def validate_cfop(self, cfop: str) -> Tuple[bool, str, Dict]:
        """
        Valida código CFOP (4 dígitos).

        Args:
            cfop: Código CFOP

        Returns:
            Tupla (válido, mensagem, detalhes)
        """
        cfop_clean = re.sub(r'[^0-9]', '', cfop) if cfop else ''

        if len(cfop_clean) != 4:
            return (
                False,
                f'CFOP deve ter 4 dígitos (encontrado: {len(cfop_clean)})',
                {},
            )

        primeiro_digito = cfop_clean[0]

        details = {'tipo_operacao': '', 'natureza': ''}

        if primeiro_digito in '123':
            details['tipo_operacao'] = 'entrada'
            if primeiro_digito == '1':
                details['natureza'] = 'entrada_dentro_estado'
            elif primeiro_digito == '2':
                details['natureza'] = 'entrada_outros_estados'
            else:
                details['natureza'] = 'entrada_exterior'
        elif primeiro_digito in '567':
            details['tipo_operacao'] = 'saida'
            if primeiro_digito == '5':
                details['natureza'] = 'saida_dentro_estado'
            elif primeiro_digito == '6':
                details['natureza'] = 'saida_outros_estados'
            else:
                details['natureza'] = 'saida_exterior'
        else:
            return (
                False,
                f'Primeiro dígito do CFOP inválido: {primeiro_digito}',
                details,
            )

        return True, 'CFOP válido', details

    def validate_date_format(
        self, date_str: str, field_name: str
    ) -> Tuple[bool, str]:
        """
        Valida formato de data (YYYY-MM-DD ou DD/MM/YYYY).

        Args:
            date_str: String de data
            field_name: Nome do campo para mensagem

        Returns:
            Tupla (válido, mensagem)
        """
        if not date_str:
            return False, f'{field_name} não pode estar vazio'

        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True, f'{field_name} válida'
        except ValueError:
            pass

        try:
            datetime.strptime(date_str, '%d/%m/%Y')
            return True, f'{field_name} válida'
        except ValueError:
            return (
                False,
                f'{field_name} com formato inválido (use YYYY-MM-DD ou DD/MM/YYYY)',
            )

    def validate_product_calculation(
        self,
        quantidade: float,
        valor_unitario: float,
        valor_total: float,
        produto_desc: str = 'Produto',
        tolerance: float = 0.02,
    ) -> Tuple[bool, str, Dict]:
        """
        Valida cálculo: quantidade × valor_unitario = valor_total.

        Args:
            quantidade: Quantidade do produto
            valor_unitario: Valor unitário
            valor_total: Valor total declarado
            produto_desc: Descrição do produto
            tolerance: Tolerância para arredondamento

        Returns:
            Tupla (válido, mensagem, detalhes)
        """
        quantidade = self._safe_float(quantidade, 0.0)
        valor_unitario = self._safe_float(valor_unitario, 0.0)
        valor_total = self._safe_float(valor_total, 0.0)

        expected_total = round(
            Decimal(str(quantidade)) * Decimal(str(valor_unitario)), 2
        )
        expected_total = float(expected_total)

        difference = abs(expected_total - valor_total)

        details = {
            'quantidade': quantidade,
            'valor_unitario': valor_unitario,
            'valor_declarado': valor_total,
            'valor_calculado': expected_total,
            'diferenca': difference,
        }

        if difference > tolerance:
            return (
                False,
                f'{produto_desc}: Valor total incorreto (esperado: R$ {expected_total:.2f}, declarado: R$ {valor_total:.2f})',
                details,
            )

        return True, f'{produto_desc}: Cálculo correto', details

    def _safe_float(self, value, default=0.0) -> float:
        """
        Converte valor para float, tratando None e strings.

        Args:
            value: Valor a converter
            default: Valor padrão se conversão falhar

        Returns:
            Float convertido ou valor padrão
        """
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def validate_tax_calculation(
        self,
        base_calculo: float,
        aliquota: float,
        valor_imposto: float,
        tipo_imposto: str,
        tolerance: float = 0.02,
    ) -> Tuple[bool, str, Dict]:
        """
        Valida cálculo de imposto: base × (alíquota/100) = valor_imposto.

        Args:
            base_calculo: Base de cálculo
            aliquota: Alíquota em percentual
            valor_imposto: Valor do imposto declarado
            tipo_imposto: Tipo do imposto (ICMS, IPI, etc)
            tolerance: Tolerância para arredondamento

        Returns:
            Tupla (válido, mensagem, detalhes)
        """
        base_calculo = self._safe_float(base_calculo, 0.0)
        aliquota = self._safe_float(aliquota, 0.0)
        valor_imposto = self._safe_float(valor_imposto, 0.0)

        if base_calculo == 0:
            if valor_imposto == 0:
                return (
                    True,
                    f'{tipo_imposto}: Sem base de cálculo (correto)',
                    {},
                )
            else:
                return (
                    False,
                    f'{tipo_imposto}: Base zero mas imposto declarado',
                    {},
                )

        expected_tax = round(
            Decimal(str(base_calculo)) * Decimal(str(aliquota)) / 100, 2
        )
        expected_tax = float(expected_tax)

        difference = abs(expected_tax - valor_imposto)

        details = {
            'base_calculo': base_calculo,
            'aliquota': aliquota,
            'valor_calculado': expected_tax,
            'valor_declarado': valor_imposto,
            'diferenca': difference,
        }

        if difference > tolerance:
            return (
                False,
                f'{tipo_imposto}: Valor incorreto (esperado: R$ {expected_tax:.2f}, declarado: R$ {valor_imposto:.2f})',
                details,
            )

        return True, f'{tipo_imposto}: Cálculo correto', details

    def get_icms_aliquota(
        self, uf: str, operacao_tipo: str = 'interno'
    ) -> float:
        """
        Retorna a alíquota de ICMS apropriada para o estado.

        Args:
            uf: Sigla do estado
            operacao_tipo: 'interno' ou 'interestadual'

        Returns:
            Alíquota de ICMS
        """
        if operacao_tipo == 'interno':
            return self.tax_rates['icms_interno'].get(
                uf.upper(), self.tax_rates['icms_interno']['default']
            )
        else:
            return self.tax_rates['icms_interestadual']['sul_sudeste']

    def validate_total_sum(
        self,
        items_total: float,
        declared_total: float,
        field_name: str = 'Total',
        tolerance: float = 0.02,
    ) -> Tuple[bool, str, Dict]:
        """
        Valida soma de totais.

        Args:
            items_total: Soma calculada dos itens
            declared_total: Total declarado
            field_name: Nome do campo
            tolerance: Tolerância

        Returns:
            Tupla (válido, mensagem, detalhes)
        """
        items_total = self._safe_float(items_total, 0.0)
        declared_total = self._safe_float(declared_total, 0.0)

        difference = abs(items_total - declared_total)

        details = {
            'soma_calculada': items_total,
            'total_declarado': declared_total,
            'diferenca': difference,
        }

        if difference > tolerance:
            return (
                False,
                f'{field_name}: Soma incorreta (calculado: R$ {items_total:.2f}, declarado: R$ {declared_total:.2f})',
                details,
            )

        return True, f'{field_name}: Soma correta', details

    def validate_invoice(self, invoice_data: Dict) -> Dict:
        """
        Realiza validação completa de uma nota fiscal.

        Args:
            invoice_data: Dados da nota fiscal

        Returns:
            Dict com resultado da validação
        """
        self.errors = []
        self.warnings = []

        logger.info('Iniciando validação determinística da nota fiscal')

        self._validate_documents(invoice_data)
        self._validate_fiscal_codes(invoice_data)
        self._validate_products_calculations(invoice_data)
        self._validate_tax_calculations(invoice_data)
        self._validate_totals(invoice_data)
        self._validate_consistency(invoice_data)

        result = self._compile_validation_result()

        logger.info(
            f'Validação concluída: {len(self.errors)} erros, {len(self.warnings)} avisos'
        )

        return result

    def _validate_documents(self, invoice_data: Dict):
        """Valida documentos (CNPJ, CPF, Chave de Acesso)"""
        emitente = invoice_data.get('emitente', {})
        if emitente.get('cnpj'):
            valid, msg = self.validate_cnpj(emitente['cnpj'])
            if not valid:
                self.errors.append(
                    ValidationError(
                        'critico',
                        'documento',
                        'emitente.cnpj',
                        msg,
                        emitente['cnpj'],
                        None,
                        'Verifique se o CNPJ está correto',
                    )
                )

        destinatario = invoice_data.get('destinatario', {})
        tipo_doc = destinatario.get('tipo_documento', '')
        if tipo_doc:
            tipo_doc = tipo_doc.lower()
        documento = destinatario.get('documento', '')

        if tipo_doc == 'cnpj' and documento:
            valid, msg = self.validate_cnpj(documento)
            if not valid:
                self.errors.append(
                    ValidationError(
                        'critico',
                        'documento',
                        'destinatario.documento',
                        msg,
                        documento,
                        None,
                        'Verifique se o CNPJ está correto',
                    )
                )
        elif tipo_doc == 'cpf' and documento:
            valid, msg = self.validate_cpf(documento)
            if not valid:
                self.errors.append(
                    ValidationError(
                        'erro',
                        'documento',
                        'destinatario.documento',
                        msg,
                        documento,
                        None,
                        'Verifique se o CPF está correto',
                    )
                )
        elif documento and not tipo_doc:
            doc_clean = re.sub(r'[^0-9]', '', documento)
            if len(doc_clean) == 14:
                valid, msg = self.validate_cnpj(documento)
                if not valid:
                    self.errors.append(
                        ValidationError(
                            'critico',
                            'documento',
                            'destinatario.documento',
                            msg,
                            documento,
                            None,
                            'Verifique se o CNPJ está correto',
                        )
                    )
            elif len(doc_clean) == 11:
                valid, msg = self.validate_cpf(documento)
                if not valid:
                    self.errors.append(
                        ValidationError(
                            'erro',
                            'documento',
                            'destinatario.documento',
                            msg,
                            documento,
                            None,
                            'Verifique se o CPF está correto',
                        )
                    )

        identificacao = invoice_data.get('identificacao', {})
        chave = identificacao.get('chave_acesso')

        if chave is None:
            self.warnings.append(
                ValidationError(
                    'aviso',
                    'identificacao',
                    'identificacao.chave_acesso',
                    'Chave de acesso não informada',
                    'None',
                    '44 dígitos',
                    'Informe a chave de acesso da NF-e',
                )
            )
        elif chave:
            valid, msg, details = self.validate_chave_acesso(chave)
            if not valid:
                self.errors.append(
                    ValidationError(
                        'critico',
                        'identificacao',
                        'identificacao.chave_acesso',
                        msg,
                        chave,
                        None,
                        'Verifique a chave de acesso da NF-e',
                    )
                )

    def _validate_fiscal_codes(self, invoice_data: Dict):
        """Valida códigos fiscais (NCM, CFOP)"""
        produtos = invoice_data.get('produtos', [])

        for i, produto in enumerate(produtos):
            ncm = produto.get('ncm')
            if ncm is None:
                self.warnings.append(
                    ValidationError(
                        'aviso',
                        'codigo_fiscal',
                        f'produtos[{i}].ncm',
                        'NCM não informado',
                        'None',
                        '8 dígitos',
                        'Informe o código NCM do produto',
                    )
                )
            elif ncm:
                valid, msg = self.validate_ncm(ncm)
                if not valid:
                    self.warnings.append(
                        ValidationError(
                            'aviso',
                            'codigo_fiscal',
                            f'produtos[{i}].ncm',
                            msg,
                            ncm,
                            '8 dígitos',
                            'Verifique o código NCM do produto',
                        )
                    )

            cfop = produto.get('cfop')
            if cfop is None:
                self.warnings.append(
                    ValidationError(
                        'aviso',
                        'codigo_fiscal',
                        f'produtos[{i}].cfop',
                        'CFOP não informado',
                        'None',
                        '4 dígitos',
                        'Informe o código CFOP da operação',
                    )
                )
            elif cfop:
                valid, msg, details = self.validate_cfop(cfop)
                if not valid:
                    self.errors.append(
                        ValidationError(
                            'erro',
                            'codigo_fiscal',
                            f'produtos[{i}].cfop',
                            msg,
                            cfop,
                            '4 dígitos',
                            'Verifique o código CFOP',
                        )
                    )

    def _validate_products_calculations(self, invoice_data: Dict):
        """Valida cálculos dos produtos"""
        produtos = invoice_data.get('produtos', [])

        for i, produto in enumerate(produtos):
            qtd = self._safe_float(produto.get('quantidade'), 0.0)
            val_unit = self._safe_float(produto.get('valor_unitario'), 0.0)
            val_total = self._safe_float(produto.get('valor_total'), 0.0)
            desc = produto.get('descricao', f'Produto {i+1}')

            if qtd > 0 or val_unit > 0 or val_total > 0:
                valid, msg, details = self.validate_product_calculation(
                    qtd, val_unit, val_total, desc
                )

                if not valid:
                    self.errors.append(
                        ValidationError(
                            'erro',
                            'calculo',
                            f'produtos[{i}].valor_total',
                            msg,
                            f'R$ {val_total:.2f}',
                            f"R$ {details['valor_calculado']:.2f}",
                            f"Corrija o valor total para R$ {details['valor_calculado']:.2f}",
                        )
                    )

    def _validate_tax_calculations(self, invoice_data: Dict):
        """Valida cálculos de impostos - VERSÃO CORRIGIDA"""
        totais = invoice_data.get('totais', {})
        emitente = invoice_data.get('emitente', {})

        uf_emitente = emitente.get('uf', '').upper()

        base_icms = self._safe_float(totais.get('base_calculo_icms'), 0.0)
        valor_icms = self._safe_float(totais.get('valor_icms'), 0.0)
        aliquota_icms_declarada = self._safe_float(
            totais.get('aliquota_icms'), 0.0
        )

        if base_icms > 0 and valor_icms > 0:
            aliquota_esperada = self.get_icms_aliquota(uf_emitente, 'interno')

            if aliquota_icms_declarada > 0:
                valid, msg, details = self.validate_tax_calculation(
                    base_icms, aliquota_icms_declarada, valor_icms, 'ICMS'
                )

                if not valid:
                    self.errors.append(
                        ValidationError(
                            'erro',
                            'imposto',
                            'totais.valor_icms',
                            msg,
                            f'R$ {valor_icms:.2f}',
                            f"R$ {details['valor_calculado']:.2f}",
                            f'Verifique o cálculo do ICMS',
                        )
                    )

                if not (7 <= aliquota_icms_declarada <= 25):
                    self.warnings.append(
                        ValidationError(
                            'aviso',
                            'imposto',
                            'totais.aliquota_icms',
                            f'Alíquota de ICMS incomum: {aliquota_icms_declarada:.2f}% (esperado para {uf_emitente}: {aliquota_esperada:.2f}%)',
                            f'{aliquota_icms_declarada:.2f}%',
                            f'{aliquota_esperada:.2f}%',
                            f'Verifique se a alíquota está correta para o tipo de produto',
                        )
                    )
            else:
                valid, msg, details = self.validate_tax_calculation(
                    base_icms,
                    aliquota_esperada,
                    valor_icms,
                    f'ICMS (esperado {aliquota_esperada}% para {uf_emitente})',
                )

                if not valid:
                    self.errors.append(
                        ValidationError(
                            'erro',
                            'imposto',
                            'totais.valor_icms',
                            msg,
                            f'R$ {valor_icms:.2f}',
                            f"R$ {details['valor_calculado']:.2f}",
                            f'Verifique o cálculo do ICMS para {uf_emitente}',
                        )
                    )

        base_pis = self._safe_float(totais.get('base_calculo_pis'), 0.0)
        valor_pis = self._safe_float(totais.get('valor_pis'), 0.0)
        aliquota_pis = self._safe_float(totais.get('aliquota_pis'), 0.0)

        if base_pis > 0 and valor_pis > 0:
            if aliquota_pis == 0.0:
                aliquota_pis = self.tax_rates['pis_padrao']

            valid, msg, details = self.validate_tax_calculation(
                base_pis, aliquota_pis, valor_pis, 'PIS'
            )

            if not valid:
                self.errors.append(
                    ValidationError(
                        'erro',
                        'imposto',
                        'totais.valor_pis',
                        msg,
                        f'R$ {valor_pis:.2f}',
                        f"R$ {details['valor_calculado']:.2f}",
                        f'Verifique o cálculo do PIS',
                    )
                )

            if aliquota_pis not in [0.65, 1.65]:
                self.warnings.append(
                    ValidationError(
                        'aviso',
                        'imposto',
                        'totais.aliquota_pis',
                        f'Alíquota de PIS incomum: {aliquota_pis:.2f}% (esperado: 0,65% ou 1,65%)',
                        f'{aliquota_pis:.2f}%',
                        '0,65% ou 1,65%',
                        'Verifique se é regime cumulativo (0,65%) ou não-cumulativo (1,65%)',
                    )
                )

        base_cofins = self._safe_float(totais.get('base_calculo_cofins'), 0.0)
        valor_cofins = self._safe_float(totais.get('valor_cofins'), 0.0)
        aliquota_cofins = self._safe_float(totais.get('aliquota_cofins'), 0.0)

        if base_cofins > 0 and valor_cofins > 0:
            if aliquota_cofins == 0.0:
                aliquota_cofins = self.tax_rates['cofins_padrao']

            valid, msg, details = self.validate_tax_calculation(
                base_cofins, aliquota_cofins, valor_cofins, 'COFINS'
            )

            if not valid:
                self.errors.append(
                    ValidationError(
                        'erro',
                        'imposto',
                        'totais.valor_cofins',
                        msg,
                        f'R$ {valor_cofins:.2f}',
                        f"R$ {details['valor_calculado']:.2f}",
                        'Verifique o cálculo do COFINS',
                    )
                )

            if aliquota_cofins not in [3.0, 7.6]:
                self.warnings.append(
                    ValidationError(
                        'aviso',
                        'imposto',
                        'totais.aliquota_cofins',
                        f'Alíquota de COFINS incomum: {aliquota_cofins:.2f}% (esperado: 3,0% ou 7,6%)',
                        f'{aliquota_cofins:.2f}%',
                        '3,0% ou 7,6%',
                        'Verifique se é regime cumulativo (3,0%) ou não-cumulativo (7,6%)',
                    )
                )

    def _validate_totals(self, invoice_data: Dict):
        """Valida totalizadores"""
        produtos = invoice_data.get('produtos', [])
        totais = invoice_data.get('totais', {})

        sum_produtos = sum(
            self._safe_float(p.get('valor_total'), 0.0) for p in produtos
        )
        valor_produtos = self._safe_float(totais.get('valor_produtos'), 0.0)

        if sum_produtos > 0 or valor_produtos > 0:
            valid, msg, details = self.validate_total_sum(
                sum_produtos, valor_produtos, 'Valor dos Produtos'
            )

            if not valid:
                self.errors.append(
                    ValidationError(
                        'erro',
                        'totalizador',
                        'totais.valor_produtos',
                        msg,
                        f'R$ {valor_produtos:.2f}',
                        f'R$ {sum_produtos:.2f}',
                        f'Corrija para R$ {sum_produtos:.2f}',
                    )
                )

        if totais.get('valor_produtos') is None and len(produtos) > 0:
            self.warnings.append(
                ValidationError(
                    'aviso',
                    'totalizador',
                    'totais.valor_produtos',
                    'Campo valor_produtos está ausente',
                    'None',
                    f'R$ {sum_produtos:.2f}',
                    'Preencha o campo com o valor correto',
                )
            )

    def _validate_consistency(self, invoice_data: Dict):
        """Valida consistências entre campos"""
        identificacao = invoice_data.get('identificacao', {})
        tipo_op = identificacao.get('tipo_operacao')

        if tipo_op is None:
            self.warnings.append(
                ValidationError(
                    'aviso',
                    'identificacao',
                    'identificacao.tipo_operacao',
                    'Tipo de operação não informado',
                    'None',
                    'entrada ou saida',
                    'Informe o tipo de operação da nota',
                )
            )
            return

        tipo_op = tipo_op.lower()

        produtos = invoice_data.get('produtos', [])
        for i, produto in enumerate(produtos):
            cfop = produto.get('cfop')
            if cfop:
                valid, msg, details = self.validate_cfop(cfop)
                if valid:
                    cfop_tipo = details.get('tipo_operacao', '')
                    if cfop_tipo and cfop_tipo != tipo_op:
                        self.errors.append(
                            ValidationError(
                                'erro',
                                'consistencia',
                                f'produtos[{i}].cfop',
                                f'CFOP {cfop} indica {cfop_tipo} mas nota é de {tipo_op}',
                                cfop,
                                None,
                                f'Use CFOP compatível com {tipo_op}',
                            )
                        )

    def _compile_validation_result(self) -> Dict:
        """Compila resultado final da validação"""
        total_errors = len(
            [e for e in self.errors if e.severity in ['critico', 'erro']]
        )
        total_warnings = len(
            [e for e in self.errors if e.severity == 'aviso']
        ) + len(self.warnings)
        total_critical = len(
            [e for e in self.errors if e.severity == 'critico']
        )

        score = 100
        score -= total_critical * 25
        score -= (total_errors - total_critical) * 10
        score -= total_warnings * 3
        score = max(0, score)

        if total_critical > 0:
            status = 'invalido'
            apto = False
        elif total_errors > 0:
            status = 'invalido'
            apto = False
        elif total_warnings > 0:
            status = 'com_avisos'
            apto = True
        else:
            status = 'valido'
            apto = True

        return {
            'validacao_geral': {
                'status': status,
                'score_conformidade': score,
                'total_erros_criticos': total_critical,
                'total_erros': total_errors - total_critical,
                'total_avisos': total_warnings,
                'apto_para_processamento': apto,
            },
            'problemas': [e.to_dict() for e in self.errors]
            + [w.to_dict() for w in self.warnings],
            'timestamp': datetime.now().isoformat(),
            'validador': 'FiscalValidator v2.0 (Corrigido e Atualizado 2024-2025)',
        }
