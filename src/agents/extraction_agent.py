import json
import logging
from pathlib import Path
from typing import Dict, List

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.media import File
from agno.models.google import Gemini
from dotenv import load_dotenv

from output_parser.fiscal_extraction_parser import NotaFiscalExtract

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FiscalExtractionAgent:
    """
    Agente especializado em extrair dados estruturados de notas fiscais.
    Suporta XML, PDF e imagens de NF-e.
    """

    def __init__(self):
        """
        Inicializa o agente de extração.
        """
        self.agent = Agent(
            name="Fiscal Extraction Specialist",
            model=Gemini(id="gemini-2.0-flash"),
            db=InMemoryDb(),
            markdown=True,
            instructions=self._get_extraction_instructions(),
            output_schema=NotaFiscalExtract,
            add_history_to_context=True,
        )

        logger.info("Agente de Extração inicializado...")

    def _get_extraction_instructions(self) -> str:
        """
        Retorna as instruções detalhadas para o agente.
        """
        return """
        Você é um especialista em análise de documentos fiscais brasileiros, especialmente Notas Fiscais Eletrônicas (NF-e).
        
        Sua missão é extrair TODOS os dados relevantes do documento fiscal anexado, seguindo estas diretrizes:
        
        ## PRIORIDADE MÁXIMA - Campos Obrigatórios:
        1. **Identificação da Nota**:
           - Número da NF
           - Série
           - Data de emissão
           - Chave de acesso (44 dígitos)
           - Tipo de operação (entrada/saída)
        
        2. **Emitente**:
           - CNPJ (formatar: XX.XXX.XXX/XXXX-XX)
           - Razão Social
           - Nome Fantasia
           - Inscrição Estadual
           - Endereço completo (logradouro, número, bairro, cidade, UF, CEP)
        
        3. **Destinatário**:
           - CNPJ ou CPF
           - Nome/Razão Social
           - Endereço completo
           - Inscrição Estadual (se houver)
        
        4. **Produtos/Serviços**:
           Para CADA item, extrair:
           - Código do produto
           - Descrição
           - NCM (Nomenclatura Comum do Mercosul)
           - CFOP (Código Fiscal de Operações e Prestações)
           - Unidade
           - Quantidade
           - Valor unitário
           - Valor total
           - Impostos do item (ICMS, IPI, PIS, COFINS)
        
        5. **Valores Totais**:
           - Valor total dos produtos
           - Valor total da nota
           - Base de cálculo ICMS
           - Valor ICMS
           - Base de cálculo ICMS ST
           - Valor ICMS ST
           - Valor IPI
           - Valor PIS
           - Valor COFINS
           - Valor do frete
           - Valor do seguro
           - Desconto
           - Outras despesas
        
        6. **Informações Adicionais**:
           - Informações complementares
           - Observações fiscais
           - Forma de pagamento
           - Transportadora (se houver)
        
        ## REGRAS DE EXTRAÇÃO:
        - Se o documento for um XML, procure pelos nós específicos da NF-e
        - Se for PDF ou imagem, identifique visualmente os campos
        - SEMPRE valide CNPJs (14 dígitos) e CPFs (11 dígitos)
        - Converta valores monetários para float (usar ponto como separador decimal)
        - Datas devem estar no formato ISO: YYYY-MM-DD
        - Se um campo não existir no documento, deixe como None
        - Para campos numéricos vazios, retorne 0.0
        
        ## VALIDAÇÕES:
        - A soma dos valores dos produtos deve bater com o valor total
        - CNPJ/CPF devem ter o número correto de dígitos
        - A chave de acesso deve ter exatamente 44 dígitos
        - NCM deve ter 8 dígitos
        - CFOP deve ter 4 dígitos
        
        ## IMPORTANTE:
        Retorne os dados estruturados conforme o schema definido.
        Não faça suposições - extraia apenas o que está explicitamente no documento.
        """

    def extract_from_file(self, file_path: str) -> Dict:
        """
        Extrai dados de um arquivo local.

        Args:
            file_path: Caminho para o arquivo (XML, PDF ou imagem)

        Returns:
            Dict com os dados extraídos estruturados
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        logger.info(f"Processando arquivo: {path.name}")

        file_extension = path.suffix.lower()

        if file_extension == ".xml":
            prompt = """
            Analise o arquivo XML de NF-e anexado e extraia TODOS os dados fiscais.
            Este é um XML estruturado, então procure pelos nós específicos como:
            - nfeProc/NFe/infNFe para informações principais
            - emit para dados do emitente
            - dest para dados do destinatário
            - det para produtos
            - total para valores totais
            """
        elif file_extension == ".pdf":
            prompt = """
            Analise o PDF de nota fiscal anexado e extraia TODOS os dados fiscais visíveis.
            Identifique visualmente cada campo e seção do documento.
            Preste atenção especial na tabela de produtos e nos valores totais.
            """
        else:
            prompt = """
            Analise a imagem da nota fiscal anexada e extraia TODOS os dados fiscais visíveis.
            Use OCR para ler o texto e identifique cada campo baseado em sua posição e rótulo.
            Se algum texto estiver difícil de ler, tente inferir baseado no contexto.
            """

        try:
            response = self.agent.run(prompt, files=[File(filepath=path)], stream=False)

            # Com response_model, o agno já retorna um objeto Pydantic
            if isinstance(response.content, NotaFiscalExtract):
                result = response.content.model_dump()
            elif hasattr(response, "content"):
                result = response.content
            else:
                result = {"raw_response": str(response)}

            # Adicionar metadata do arquivo
            if isinstance(result, dict) and "metadata" in result:
                result["metadata"]["formato_original"] = file_extension.replace(".", "")
                result["metadata"]["arquivo_processado"] = path.name

            logger.info(f"Extração concluída para: {path.name}")
            return result

        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {e}")
            raise

    def extract_from_bytes(
        self, file_bytes: bytes, filename: str = "nota_fiscal"
    ) -> Dict:
        """
        Extrai dados de bytes de arquivo.

        Args:
            file_bytes: Bytes do arquivo
            filename: Nome do arquivo para identificação

        Returns:
            Dict com os dados extraídos
        """
        logger.info(f"Processando arquivo em bytes: {filename}")

        prompt = """
        Analise o documento fiscal anexado e extraia TODOS os dados conforme as instruções.
        Identifique automaticamente o tipo de documento (XML, PDF ou imagem) e processe adequadamente.
        """

        try:
            response = self.agent.run(
                prompt, files=[File(content=file_bytes)], stream=False
            )

            if isinstance(response.content, NotaFiscalExtract):
                result = response.content.model_dump()
            elif hasattr(response, "content"):
                result = response.content
            else:
                result = {"raw_response": str(response)}

            logger.info(f"Extração concluída para: {filename}")
            return result

        except Exception as e:
            logger.error(f"Erro ao processar bytes: {e}")
            raise

    def extract_batch(self, file_paths: List[str]) -> List[Dict]:
        """
        Processa múltiplos arquivos em lote.

        Args:
            file_paths: Lista de caminhos de arquivos

        Returns:
            Lista de dicts com dados extraídos
        """
        results = []

        for file_path in file_paths:
            try:
                result = self.extract_from_file(file_path)
                results.append(
                    {
                        "arquivo": file_path,
                        "status": "sucesso",
                        "dados": result,
                    }
                )
            except Exception as e:
                logger.error(f"Erro ao processar {file_path}: {e}")
                results.append({"arquivo": file_path, "status": "erro", "erro": str(e)})

        return results

    def validate_extraction(self, extracted_data: Dict) -> Dict:
        """
        Valida os dados extraídos.

        Args:
            extracted_data: Dados extraídos

        Returns:
            Dict com resultado da validação
        """
        validation_prompt = f"""
        Valide os seguintes dados extraídos de uma nota fiscal:
        
        {json.dumps(extracted_data, indent=2, ensure_ascii=False)}
        
        Verifique:
        1. CNPJ/CPF estão com formato correto?
        2. Chave de acesso tem 44 dígitos?
        3. NCM tem 8 dígitos?
        4. CFOP tem 4 dígitos?
        5. A soma dos produtos bate com o valor total?
        6. Todos os campos obrigatórios estão preenchidos?
        
        Retorne um JSON com:
        - valido: true/false
        - problemas: lista de problemas encontrados
        - sugestoes: correções sugeridas
        """

        response = self.agent.run(validation_prompt, stream=False)

        try:
            return json.loads(
                response.content if hasattr(response, "content") else str(response)
            )
        except:
            return {
                "valido": False,
                "problemas": ["Não foi possível validar"],
                "sugestoes": [],
            }


# Exemplo de uso
if __name__ == "__main__":
    # Criar o agente
    extractor = FiscalExtractionAgent()

    # Exemplo 1: Processar um PDF
    resultado = extractor.extract_from_file(
        "35250531152562000346550010000113341000440803-nfe.pdf"
    )
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    # Exemplo 2: Processar múltiplos arquivos
    # arquivos = ["nota1.xml", "nota2.pdf", "nota3.jpg"]
    # resultados = extractor.extract_batch(arquivos)

    # Exemplo 3: Validar extração
    # validacao = extractor.validate_extraction(resultado)
    # print(validacao)
