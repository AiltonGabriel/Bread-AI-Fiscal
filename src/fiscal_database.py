import sqlite3
import json
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FiscalDatabase:
    """
    Gerenciador de banco de dados SQLite para sistema fiscal.
    
    Estrutura:
    - notas_fiscais: Dados extraídos das notas
    - validacoes: Resultados de validação determinística
    - analises_contextuais: Análises contextuais (nota individual)
    - analises_negocio: Análises de negócio (múltiplas notas)
    - produtos: Produtos das notas
    - alertas: Alertas e problemas identificados
    - recomendacoes: Recomendações geradas
    """
    
    def __init__(self, db_path: str = "fiscal_data.db"):
        """
        Inicializa conexão com banco de dados.
        
        Args:
            db_path: Caminho para arquivo do banco SQLite
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
        logger.info(f"Database inicializado: {db_path}")
    
    def _connect(self):
        """Conecta ao banco de dados"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Retorna dicts
        
    def _create_tables(self):
        """Cria todas as tabelas necessárias"""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notas_fiscais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Identificação
                numero_nf TEXT,
                serie TEXT,
                chave_acesso TEXT UNIQUE,
                data_emissao DATE,
                tipo_operacao TEXT,
                natureza_operacao TEXT,
                
                -- Emitente
                emitente_cnpj TEXT,
                emitente_razao_social TEXT,
                emitente_uf TEXT,
                
                -- Destinatário
                destinatario_documento TEXT,
                destinatario_tipo_documento TEXT,
                destinatario_nome TEXT,
                destinatario_uf TEXT,
                
                -- Totais
                valor_total_nf REAL,
                valor_produtos REAL,
                valor_icms REAL,
                valor_icms_st REAL,
                valor_ipi REAL,
                valor_pis REAL,
                valor_cofins REAL,
                valor_frete REAL,
                valor_desconto REAL,
                
                -- Metadata
                arquivo_origem TEXT,
                formato_original TEXT,
                confianca_extracao REAL,
                data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- JSON completo (backup)
                dados_completos_json TEXT,
                
                -- Índices
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota_fiscal_id INTEGER NOT NULL,
                
                codigo TEXT,
                descricao TEXT,
                ncm TEXT,
                cfop TEXT,
                unidade TEXT,
                quantidade REAL,
                valor_unitario REAL,
                valor_total REAL,
                
                -- Impostos do produto
                icms REAL,
                ipi REAL,
                pis REAL,
                cofins REAL,
                
                ordem_na_nota INTEGER,
                
                FOREIGN KEY (nota_fiscal_id) REFERENCES notas_fiscais(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota_fiscal_id INTEGER NOT NULL,
                
                -- Resultado geral
                status TEXT,  -- valido, invalido, com_avisos
                score_conformidade REAL,
                total_erros_criticos INTEGER,
                total_erros INTEGER,
                total_avisos INTEGER,
                apto_processamento BOOLEAN,
                
                -- Análise de risco
                nivel_risco TEXT,  -- baixo, medio, alto, critico
                necessita_revisao_manual BOOLEAN,
                necessita_correcao_urgente BOOLEAN,
                
                -- Metadata
                versao_validador TEXT,
                tempo_processamento_ms INTEGER,
                data_validacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- JSON completo
                resultado_completo_json TEXT,
                
                FOREIGN KEY (nota_fiscal_id) REFERENCES notas_fiscais(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS problemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validacao_id INTEGER,
                analise_id INTEGER,
                
                tipo TEXT,  -- validacao, analise_contextual, analise_negocio
                severidade TEXT,  -- critico, erro, aviso, info
                categoria TEXT,
                campo TEXT,
                descricao TEXT,
                valor_atual TEXT,
                valor_esperado TEXT,
                sugestao_correcao TEXT,
                impacto_fiscal TEXT,
                
                data_deteccao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (validacao_id) REFERENCES validacoes(id) ON DELETE CASCADE,
                FOREIGN KEY (analise_id) REFERENCES analises_contextuais(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analises_contextuais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota_fiscal_id INTEGER NOT NULL,
                validacao_id INTEGER,
                
                -- Resultado
                status_geral TEXT,
                nivel_risco TEXT,
                score_conformidade REAL,
                
                -- Oportunidades
                total_oportunidades INTEGER,
                economia_potencial_estimada REAL,
                
                -- Metadata
                tempo_processamento_ms INTEGER,
                data_analise TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- JSON completo
                resultado_completo_json TEXT,
                
                FOREIGN KEY (nota_fiscal_id) REFERENCES notas_fiscais(id) ON DELETE CASCADE,
                FOREIGN KEY (validacao_id) REFERENCES validacoes(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analises_negocio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Período analisado
                periodo_inicio DATE,
                periodo_fim DATE,
                total_notas_analisadas INTEGER,
                
                -- Resumo executivo
                faturamento_total REAL,
                impostos_totais REAL,
                carga_tributaria REAL,
                status_geral TEXT,
                
                -- Análise financeira
                tendencia TEXT,  -- crescimento, estavel, queda
                margem_bruta REAL,
                margem_liquida REAL,
                
                -- Análise tributária
                regime_recomendado TEXT,
                economia_potencial_anual REAL,
                
                -- Totais
                total_oportunidades INTEGER,
                total_alertas INTEGER,
                total_recomendacoes INTEGER,
                
                -- Metadata
                tempo_processamento_ms INTEGER,
                data_analise TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- JSON completo
                resultado_completo_json TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analise_negocio_notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analise_negocio_id INTEGER NOT NULL,
                nota_fiscal_id INTEGER NOT NULL,
                
                FOREIGN KEY (analise_negocio_id) REFERENCES analises_negocio(id) ON DELETE CASCADE,
                FOREIGN KEY (nota_fiscal_id) REFERENCES notas_fiscais(id) ON DELETE CASCADE,
                UNIQUE(analise_negocio_id, nota_fiscal_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recomendacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analise_contextual_id INTEGER,
                analise_negocio_id INTEGER,
                
                prioridade TEXT,  -- alta, media, baixa
                area TEXT,  -- tributaria, financeira, operacional
                acao TEXT,
                beneficio_estimado TEXT,
                prazo_implementacao TEXT,
                complexidade TEXT,  -- baixa, media, alta
                
                status TEXT DEFAULT 'pendente',  -- pendente, em_andamento, concluida, cancelada
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (analise_contextual_id) REFERENCES analises_contextuais(id) ON DELETE CASCADE,
                FOREIGN KEY (analise_negocio_id) REFERENCES analises_negocio(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nf_chave ON notas_fiscais(chave_acesso)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nf_emitente ON notas_fiscais(emitente_cnpj)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nf_data ON notas_fiscais(data_emissao)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_produtos_nota ON produtos(nota_fiscal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_validacoes_nota ON validacoes(nota_fiscal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_problemas_validacao ON problemas(validacao_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analises_nota ON analises_contextuais(nota_fiscal_id)")
        
        self.conn.commit()
        logger.info("Tabelas criadas/verificadas com sucesso")
    
    def nota_exists(self, chave_acesso: str) -> Optional[int]:
        """
        Verifica se nota já existe no banco.
        
        Args:
            chave_acesso: Chave de acesso da nota (44 dígitos)
        
        Returns:
            ID da nota se existir, None caso contrário
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM notas_fiscais WHERE chave_acesso = ?", (chave_acesso,))
        row = cursor.fetchone()
        return row['id'] if row else None
    
    def save_extraction(self, extraction_data: Dict, update_if_exists: bool = True, skip_if_exists: bool = False) -> int:
        """
        Salva resultado da extração (FiscalExtractionAgent).
        
        Args:
            extraction_data: Dict com dados extraídos (schema NotaFiscalExtract)
            update_if_exists: Se True, atualiza nota existente (padrão: True)
            skip_if_exists: Se True, retorna ID existente sem atualizar (padrão: False)
                           Tem prioridade sobre update_if_exists
        
        Returns:
            ID da nota fiscal salva ou existente
        """
        cursor = self.conn.cursor()

        extraction_data = self._convert_enums_to_strings(extraction_data)

        identificacao = extraction_data.get('identificacao', {})
        emitente = extraction_data.get('emitente', {})
        destinatario = extraction_data.get('destinatario', {})
        totais = extraction_data.get('totais', {})
        metadata = extraction_data.get('metadata', {})
        produtos = extraction_data.get('produtos', [])
        
        chave_acesso = identificacao.get('chave_acesso')

        existing_id = self.nota_exists(chave_acesso) if chave_acesso else None
        
        if existing_id:
            if skip_if_exists:
                logger.info(f"Nota já existe: nota_fiscal_id={existing_id}, chave={chave_acesso} (pulando)")
                return existing_id
            elif update_if_exists:
                logger.info(f"Nota já existe: nota_fiscal_id={existing_id}, chave={chave_acesso} (atualizando)")
                cursor.execute("""
                    UPDATE notas_fiscais SET
                        numero_nf = ?, serie = ?, data_emissao = ?, tipo_operacao = ?, natureza_operacao = ?,
                        emitente_cnpj = ?, emitente_razao_social = ?, emitente_uf = ?,
                        destinatario_documento = ?, destinatario_tipo_documento = ?, destinatario_nome = ?, destinatario_uf = ?,
                        valor_total_nf = ?, valor_produtos = ?, valor_icms = ?, valor_icms_st = ?, valor_ipi = ?, 
                        valor_pis = ?, valor_cofins = ?, valor_frete = ?, valor_desconto = ?,
                        arquivo_origem = ?, formato_original = ?, confianca_extracao = ?,
                        dados_completos_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    identificacao.get('numero_nf'),
                    identificacao.get('serie'),
                    identificacao.get('data_emissao'),
                    identificacao.get('tipo_operacao'),
                    identificacao.get('natureza_operacao'),
                    emitente.get('cnpj'),
                    emitente.get('razao_social'),
                    emitente.get('endereco', {}).get('uf') if emitente.get('endereco') else None,
                    destinatario.get('documento'),
                    destinatario.get('tipo_documento'),
                    destinatario.get('nome'),
                    destinatario.get('endereco', {}).get('uf') if destinatario.get('endereco') else None,
                    totais.get('valor_total_nf'),
                    totais.get('valor_produtos'),
                    totais.get('valor_icms'),
                    totais.get('valor_icms_st'),
                    totais.get('valor_ipi'),
                    totais.get('valor_pis'),
                    totais.get('valor_cofins'),
                    totais.get('valor_frete'),
                    totais.get('valor_desconto'),
                    metadata.get('arquivo_processado'),
                    metadata.get('formato_original'),
                    metadata.get('confianca_extracao'),
                    json.dumps(extraction_data, ensure_ascii=False),
                    existing_id
                ))

                cursor.execute("DELETE FROM produtos WHERE nota_fiscal_id = ?", (existing_id,))
                
                for idx, produto in enumerate(produtos):
                    impostos = produto.get('impostos', {})
                    cursor.execute("""
                        INSERT INTO produtos (
                            nota_fiscal_id, codigo, descricao, ncm, cfop, unidade,
                            quantidade, valor_unitario, valor_total,
                            icms, ipi, pis, cofins, ordem_na_nota
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        existing_id,
                        produto.get('codigo'),
                        produto.get('descricao'),
                        produto.get('ncm'),
                        produto.get('cfop'),
                        produto.get('unidade'),
                        produto.get('quantidade'),
                        produto.get('valor_unitario'),
                        produto.get('valor_total'),
                        impostos.get('icms'),
                        impostos.get('ipi'),
                        impostos.get('pis'),
                        impostos.get('cofins'),
                        idx
                    ))
                
                self.conn.commit()
                logger.info(f"Nota atualizada: nota_fiscal_id={existing_id}, chave={chave_acesso}")
                return existing_id

        cursor.execute("""
            INSERT INTO notas_fiscais (
                numero_nf, serie, chave_acesso, data_emissao, tipo_operacao, natureza_operacao,
                emitente_cnpj, emitente_razao_social, emitente_uf,
                destinatario_documento, destinatario_tipo_documento, destinatario_nome, destinatario_uf,
                valor_total_nf, valor_produtos, valor_icms, valor_icms_st, valor_ipi, 
                valor_pis, valor_cofins, valor_frete, valor_desconto,
                arquivo_origem, formato_original, confianca_extracao,
                dados_completos_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            identificacao.get('numero_nf'),
            identificacao.get('serie'),
            identificacao.get('chave_acesso'),
            identificacao.get('data_emissao'),
            identificacao.get('tipo_operacao'),
            identificacao.get('natureza_operacao'),
            emitente.get('cnpj'),
            emitente.get('razao_social'),
            emitente.get('endereco', {}).get('uf') if emitente.get('endereco') else None,
            destinatario.get('documento'),
            destinatario.get('tipo_documento'),
            destinatario.get('nome'),
            destinatario.get('endereco', {}).get('uf') if destinatario.get('endereco') else None,
            totais.get('valor_total_nf'),
            totais.get('valor_produtos'),
            totais.get('valor_icms'),
            totais.get('valor_icms_st'),
            totais.get('valor_ipi'),
            totais.get('valor_pis'),
            totais.get('valor_cofins'),
            totais.get('valor_frete'),
            totais.get('valor_desconto'),
            metadata.get('arquivo_processado'),
            metadata.get('formato_original'),
            metadata.get('confianca_extracao'),
            json.dumps(extraction_data, ensure_ascii=False)
        ))
        
        nota_fiscal_id = cursor.lastrowid

        for idx, produto in enumerate(produtos):
            impostos = produto.get('impostos', {})
            cursor.execute("""
                INSERT INTO produtos (
                    nota_fiscal_id, codigo, descricao, ncm, cfop, unidade,
                    quantidade, valor_unitario, valor_total,
                    icms, ipi, pis, cofins, ordem_na_nota
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nota_fiscal_id,
                produto.get('codigo'),
                produto.get('descricao'),
                produto.get('ncm'),
                produto.get('cfop'),
                produto.get('unidade'),
                produto.get('quantidade'),
                produto.get('valor_unitario'),
                produto.get('valor_total'),
                impostos.get('icms'),
                impostos.get('ipi'),
                impostos.get('pis'),
                impostos.get('cofins'),
                idx
            ))
        
        self.conn.commit()
        logger.info(f"Extração salva: nota_fiscal_id={nota_fiscal_id}, chave={identificacao.get('chave_acesso')}")
        
        return nota_fiscal_id
    
    def save_validation(self, nota_fiscal_id: int, validation_data: Dict) -> int:
        """
        Salva resultado da validação (FiscalValidator).
        
        Args:
            nota_fiscal_id: ID da nota fiscal
            validation_data: Dict com resultado da validação (schema NotaFiscalValidation)
        
        Returns:
            ID da validação salva
        """
        cursor = self.conn.cursor()

        validation_data = self._convert_enums_to_strings(validation_data)
        
        validacao_geral = validation_data.get('validacao_geral', {})
        analise_risco = validation_data.get('analise_risco', {})
        metadata = validation_data.get('metadata', {})
        problemas = validation_data.get('problemas', [])

        cursor.execute("""
            INSERT INTO validacoes (
                nota_fiscal_id, status, score_conformidade,
                total_erros_criticos, total_erros, total_avisos, apto_processamento,
                nivel_risco, necessita_revisao_manual, necessita_correcao_urgente,
                versao_validador, tempo_processamento_ms,
                resultado_completo_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nota_fiscal_id,
            validacao_geral.get('status'),
            validacao_geral.get('score_conformidade'),
            validacao_geral.get('total_erros_criticos'),
            validacao_geral.get('total_erros'),
            validacao_geral.get('total_avisos'),
            validacao_geral.get('apto_para_processamento'),
            analise_risco.get('nivel_risco'),
            analise_risco.get('necessita_revisao_manual'),
            analise_risco.get('necessita_correcao_urgente'),
            metadata.get('versao_validador'),
            metadata.get('tempo_processamento_ms'),
            json.dumps(validation_data, ensure_ascii=False)
        ))
        
        validacao_id = cursor.lastrowid

        for problema in problemas:
            cursor.execute("""
                INSERT INTO problemas (
                    validacao_id, tipo, severidade, categoria, campo,
                    descricao, valor_atual, valor_esperado, sugestao_correcao, impacto_fiscal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                validacao_id,
                'validacao',
                problema.get('severidade'),
                problema.get('categoria'),
                problema.get('campo'),
                problema.get('descricao'),
                problema.get('valor_atual'),
                problema.get('valor_esperado'),
                problema.get('sugestao_correcao'),
                problema.get('impacto_fiscal')
            ))
        
        self.conn.commit()
        logger.info(f"Validação salva: validacao_id={validacao_id}, status={validacao_geral.get('status')}")
        
        return validacao_id
    
    def save_contextual_analysis(self, nota_fiscal_id: int, analysis_data: Dict, validacao_id: Optional[int] = None) -> int:
        """
        Salva análise contextual (FiscalIntelligenceAgent.validate_context).
        
        Args:
            nota_fiscal_id: ID da nota fiscal
            analysis_data: Dict com análise contextual
            validacao_id: ID da validação (opcional)
        
        Returns:
            ID da análise salva
        """
        cursor = self.conn.cursor()

        analysis_data = self._convert_enums_to_strings(analysis_data)
        
        validacao_geral = analysis_data.get('validacao_geral', {})
        analise_risco = analysis_data.get('analise_risco', {})
        metadata = analysis_data.get('metadata', {})

        oportunidades = analysis_data.get('oportunidades_fiscais', [])
        total_oportunidades = len(oportunidades)
        economia_potencial = sum(op.get('economia_estimada', 0) for op in oportunidades)

        cursor.execute("""
            INSERT INTO analises_contextuais (
                nota_fiscal_id, validacao_id, status_geral, nivel_risco,
                score_conformidade, total_oportunidades, economia_potencial_estimada,
                tempo_processamento_ms, resultado_completo_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nota_fiscal_id,
            validacao_id,
            validacao_geral.get('status'),
            analise_risco.get('nivel_risco'),
            validacao_geral.get('score_conformidade'),
            total_oportunidades,
            economia_potencial,
            metadata.get('tempo_processamento_ms'),
            json.dumps(analysis_data, ensure_ascii=False)
        ))
        
        analise_id = cursor.lastrowid

        recomendacoes = analysis_data.get('recomendacoes', [])
        for rec in recomendacoes:
            cursor.execute("""
                INSERT INTO recomendacoes (
                    analise_contextual_id, prioridade, area, acao,
                    beneficio_estimado, prazo_implementacao, complexidade
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                analise_id,
                rec.get('prioridade'),
                rec.get('area'),
                rec.get('acao'),
                rec.get('beneficio_esperado'),
                rec.get('prazo_implementacao'),
                rec.get('complexidade')
            ))
        
        self.conn.commit()
        logger.info(f"Análise contextual salva: analise_id={analise_id}")
        
        return analise_id
    
    def _convert_enums_to_strings(self, data: Any) -> Any:
        """
        Converte Enums para strings recursivamente.
        
        Args:
            data: Dados a converter (dict, list, Enum, ou primitivo)
        
        Returns:
            Dados com Enums convertidos para strings
        """
        from enum import Enum
        
        if isinstance(data, Enum):
            return data.value
        elif isinstance(data, dict):
            return {k: self._convert_enums_to_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_enums_to_strings(item) for item in data]
        else:
            return data
    
    def save_business_analysis(self, analysis_data: Dict, notas_fiscais_ids: List[int]) -> int:
        """
        Salva análise de negócio (FiscalIntelligenceAgent.analyze_business).
        
        Args:
            analysis_data: Dict com análise de negócio (schema FiscalAnalysisResult)
            notas_fiscais_ids: Lista de IDs das notas analisadas
        
        Returns:
            ID da análise de negócio salva
        """
        cursor = self.conn.cursor()

        analysis_data = self._convert_enums_to_strings(analysis_data)
        
        resumo = analysis_data.get('resumo_executivo', {})
        metricas = resumo.get('principais_metricas', {})
        analise_financeira = analysis_data.get('analise_financeira', {})
        analise_tributaria = analysis_data.get('analise_tributaria', {})
        metadata = analysis_data.get('metadata', {})

        faturamento = analise_financeira.get('faturamento', {}) if analise_financeira else {}
        lucratividade = analise_financeira.get('lucratividade', {}) if analise_financeira else {}
        carga_trib = analise_tributaria.get('carga_tributaria', {}) if analise_tributaria else {}

        cursor.execute("""
            INSERT INTO analises_negocio (
                periodo_inicio, periodo_fim, total_notas_analisadas,
                faturamento_total, impostos_totais, carga_tributaria, status_geral,
                tendencia, margem_bruta, margem_liquida,
                regime_recomendado, economia_potencial_anual,
                total_oportunidades, total_alertas, total_recomendacoes,
                tempo_processamento_ms, resultado_completo_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            None,
            None,
            resumo.get('total_notas'),
            metricas.get('faturamento_total'),
            carga_trib.get('total_impostos') or metricas.get('impostos_totais'),
            carga_trib.get('percentual_sobre_faturamento') or metricas.get('carga_tributaria_efetiva'),
            resumo.get('status_geral'),
            faturamento.get('tendencia') if faturamento else None,
            lucratividade.get('margem_bruta') if lucratividade else None,
            lucratividade.get('margem_liquida_estimada') if lucratividade else None,
            analise_tributaria.get('regime_recomendado') if analise_tributaria else None,
            analise_tributaria.get('economia_potencial_anual') if analise_tributaria else None,
            len(analysis_data.get('alertas', [])),
            len(analysis_data.get('recomendacoes', [])),
            len(analysis_data.get('oportunidades_fiscais', [])) if 'oportunidades_fiscais' in analysis_data else 0,
            metadata.get('tempo_processamento_ms'),
            json.dumps(analysis_data, ensure_ascii=False)
        ))
        
        analise_negocio_id = cursor.lastrowid

        for nota_id in notas_fiscais_ids:
            cursor.execute("""
                INSERT INTO analise_negocio_notas (analise_negocio_id, nota_fiscal_id)
                VALUES (?, ?)
            """, (analise_negocio_id, nota_id))

        recomendacoes = analysis_data.get('recomendacoes', [])
        for rec in recomendacoes:
            cursor.execute("""
                INSERT INTO recomendacoes (
                    analise_negocio_id, prioridade, area, acao,
                    beneficio_estimado, prazo_implementacao, complexidade
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                analise_negocio_id,
                rec.get('prioridade'),
                rec.get('area'),
                rec.get('acao'),
                rec.get('beneficio_esperado'),
                rec.get('prazo_implementacao'),
                rec.get('complexidade')
            ))
        
        self.conn.commit()
        logger.info(f"Análise de negócio salva: analise_negocio_id={analise_negocio_id}, notas={len(notas_fiscais_ids)}")
        
        return analise_negocio_id

    def get_nota_completa(self, nota_fiscal_id: int) -> Optional[Dict]:
        """
        Busca nota fiscal com todos os dados relacionados.
        
        Returns:
            Dict com nota, produtos, validação e análises
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM notas_fiscais WHERE id = ?", (nota_fiscal_id,))
        nota = cursor.fetchone()
        
        if not nota:
            return None

        cursor.execute("SELECT * FROM produtos WHERE nota_fiscal_id = ? ORDER BY ordem_na_nota", (nota_fiscal_id,))
        produtos = cursor.fetchall()

        cursor.execute("SELECT * FROM validacoes WHERE nota_fiscal_id = ? ORDER BY data_validacao DESC LIMIT 1", (nota_fiscal_id,))
        validacao = cursor.fetchone()

        cursor.execute("SELECT * FROM analises_contextuais WHERE nota_fiscal_id = ? ORDER BY data_analise DESC LIMIT 1", (nota_fiscal_id,))
        analise = cursor.fetchone()
        
        return {
            'nota_fiscal': dict(nota),
            'produtos': [dict(p) for p in produtos],
            'validacao': dict(validacao) if validacao else None,
            'analise_contextual': dict(analise) if analise else None
        }
    
    def get_notas_por_periodo(self, data_inicio: str, data_fim: str) -> List[Dict]:
        """
        Busca notas por período.
        
        Args:
            data_inicio: Data início (YYYY-MM-DD)
            data_fim: Data fim (YYYY-MM-DD)
        
        Returns:
            Lista de notas
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notas_fiscais 
            WHERE data_emissao BETWEEN ? AND ?
            ORDER BY data_emissao DESC
        """, (data_inicio, data_fim))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_dashboard_data(self, data_inicio: str = None, data_fim: str = None) -> Dict:
        """
        Busca dados para dashboard.
        
        Returns:
            Dict com métricas agregadas
        """
        cursor = self.conn.cursor()

        where_clause = ""
        params = []
        if data_inicio and data_fim:
            where_clause = "WHERE data_emissao BETWEEN ? AND ?"
            params = [data_inicio, data_fim]

        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_notas,
                SUM(valor_total_nf) as faturamento_total,
                SUM(valor_icms + COALESCE(valor_pis, 0) + COALESCE(valor_cofins, 0)) as impostos_totais,
                AVG(valor_total_nf) as ticket_medio
            FROM notas_fiscais
            {where_clause}
        """, params)
        
        metricas = dict(cursor.fetchone())

        cursor.execute("""
            SELECT COUNT(*) as total_criticos
            FROM problemas
            WHERE severidade = 'critico'
        """)
        
        metricas['problemas_criticos'] = cursor.fetchone()['total_criticos']

        cursor.execute("""
            SELECT COUNT(*) as total_pendentes
            FROM recomendacoes
            WHERE status = 'pendente' AND prioridade = 'alta'
        """)
        
        metricas['recomendacoes_pendentes'] = cursor.fetchone()['total_pendentes']
        
        return metricas
    
    def close(self):
        """Fecha conexão com banco de dados"""
        if self.conn:
            self.conn.close()
            logger.info("Conexão com banco fechada")

if __name__ == "__main__":
    # Inicializar database
    db = FiscalDatabase("exemplo_fiscal.db")
    
    print("=" * 80)
    print("EXEMPLO DE USO DO FISCAL DATABASE")
    print("=" * 80)
    
    # 1. Simular extração
    print("\n1️⃣  Salvando extração...")
    extraction_data = {
        'identificacao': {
            'numero_nf': '000.011.334',
            'serie': '001',
            'chave_acesso': '35250531152562000346550010000113341000440803',
            'data_emissao': '2025-05-09'
        },
        'emitente': {
            'cnpj': '31.152.562/0003-46',
            'razao_social': 'NOBRE COMERCIO',
            'endereco': {'uf': 'SP'}
        },
        'destinatario': {
            'documento': '529.278.128-29',
            'tipo_documento': 'CPF',
            'nome': 'JOAO VITOR',
            'endereco': {'uf': 'SP'}
        },
        'totais': {
            'valor_total_nf': 259.78,
            'valor_produtos': 259.78,
            'valor_icms': 2.72
        },
        'produtos': [
            {
                'codigo': '90793AB42600',
                'descricao': 'OLEO YAMALUBE',
                'ncm': '27101932',
                'cfop': '5656',
                'quantidade': 1.0,
                'valor_unitario': 32.90,
                'valor_total': 32.90,
                'impostos': {'icms': 0.0}
            }
        ],
        'metadata': {
            'arquivo_processado': '35250531152562000346550010000113341000440803-nfe.pdf',
            'formato_original': 'pdf',
            'confianca_extracao': 0.95
        }
    }
    
    # Por padrão, atualiza se já existe
    nota_id = db.save_extraction(extraction_data)
    print(f"   ✅ Nota salva: ID = {nota_id}")
    
    # 2. Simular validação
    print("\n2️⃣  Salvando validação...")
    validation_data = {
        'validacao_geral': {
            'status': 'valido',
            'score_conformidade': 95.0,
            'total_erros_criticos': 0,
            'total_erros': 0,
            'total_avisos': 1,
            'apto_para_processamento': True
        },
        'analise_risco': {
            'nivel_risco': 'baixo',
            'necessita_revisao_manual': False,
            'necessita_correcao_urgente': False
        },
        'problemas': [
            {
                'severidade': 'aviso',
                'categoria': 'tributaria',
                'campo': 'valor_pis',
                'descricao': 'PIS não destacado'
            }
        ],
        'metadata': {
            'versao_validador': '2.0',
            'tempo_processamento_ms': 150
        }
    }
    
    validacao_id = db.save_validation(nota_id, validation_data)
    print(f"   ✅ Validação salva: ID = {validacao_id}")
    
    # 3. Simular análise contextual
    print("\n3️⃣  Salvando análise contextual...")
    analysis_data = {
        'validacao_geral': {
            'status': 'com_avisos',
            'score_conformidade': 90.0
        },
        'analise_risco': {
            'nivel_risco': 'medio'
        },
        'oportunidades_fiscais': [
            {
                'descricao': 'Crédito PIS/COFINS',
                'economia_estimada': 1200.0
            }
        ],
        'recomendacoes': [
            {
                'prioridade': 'alta',
                'area': 'tributaria',
                'acao': 'Solicitar crédito PIS/COFINS',
                'beneficio_esperado': 'R$ 1.200,00/ano',
                'prazo_implementacao': 'imediato',
                'complexidade': 'baixa'
            }
        ],
        'metadata': {
            'tempo_processamento_ms': 2500
        }
    }
    
    analise_id = db.save_contextual_analysis(nota_id, analysis_data, validacao_id)
    print(f"   ✅ Análise contextual salva: ID = {analise_id}")
    
    # 4. Buscar nota completa
    print("\n4️⃣  Buscando nota completa...")
    nota_completa = db.get_nota_completa(nota_id)
    print(f"   ✅ Nota encontrada:")
    print(f"      - Número: {nota_completa['nota_fiscal']['numero_nf']}")
    print(f"      - Produtos: {len(nota_completa['produtos'])}")
    print(f"      - Validação: {nota_completa['validacao']['status']}")
    print(f"      - Análise: {nota_completa['analise_contextual']['status_geral']}")
    
    # 5. Dashboard
    print("\n5️⃣  Gerando dashboard...")
    dashboard = db.get_dashboard_data()
    print(f"   ✅ Dashboard:")
    print(f"      - Total notas: {dashboard['total_notas']}")
    print(f"      - Faturamento: R$ {dashboard['faturamento_total']:,.2f}")
    print(f"      - Impostos: R$ {dashboard['impostos_totais']:,.2f}")
    print(f"      - Problemas críticos: {dashboard['problemas_criticos']}")
    print(f"      - Recomendações pendentes: {dashboard['recomendacoes_pendentes']}")
    
    # 6. Testar skip_if_exists
    print("\n6️⃣  Testando skip_if_exists...")
    nota_id_2 = db.save_extraction(extraction_data, skip_if_exists=True)
    print(f"   ✅ Nota já existia, retornou ID = {nota_id_2} (mesmo que {nota_id})")
    
    print("\n" + "=" * 80)
    print("✅ EXEMPLO CONCLUÍDO!")
    print(f"📁 Database: exemplo_fiscal.db")
    print("=" * 80)
    
    db.close()