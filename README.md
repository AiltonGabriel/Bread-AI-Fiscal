# Bread-AI-Fiscal

[![Licença](https://img.shields.io/badge/licença-MIT-blue.svg)](LICENSE) Uma plataforma de análise fiscal que utiliza Inteligência Artificial para otimizar processos, detectar anomalias e gerar insights valiosos para empresas.

---

## 📖 Índice

* [Sobre o Projeto](#sobre-o-projeto)
* [Começando](#começando)
  * [Pré-requisitos](#pré-requisitos)
  * [Instalação](#instalação)
  * [Execução](#execução)
* [Demonstração](#demonstração)
* [Licença](#licença)

---

## Sobre o Projeto

Este repositório contém o código-fonte e a documentação do projeto Bread-AI-Fiscal. Nosso objetivo é transformar a maneira como as empresas lidam com suas obrigações fiscais, utilizando modelos de IA avançados para:

## Começando

Siga estas instruções para configurar e executar a aplicação:

### Pré-requisitos

Antes de começar, certifique-se de que você tem o seguinte instalado:

* [Python](https://www.python.org/) (versão `3.13`)
* [Poetry](https://python-poetry.org/docs/#installation) (versão `2.X`) para gerenciamento de dependências

### Instalação

#### 1. Clone o repositório

```bash
git clone https://github.com/AiltonGabriel/Bread-AI-Fiscal.git
cd Bread-AI-Fiscal
```

#### 2. Configure as variáveis de ambiente

* Copie o arquivo de exemplo `.env.example` para um novo arquivo `.env`:

```bash
cp .env.example .env
```

* Edite o arquivo `.env` e preencha as variáveis necessárias.

#### 3. Instale as dependências do projeto

* O Poetry criará um ambiente virtual e instalará tudo o que está listado no `pyproject.toml`.

  ```bash
  poetry install
  ```

### Execução

Execute o comando a partir do ambiente virtual do Poetry:

```bash
poetry run streamlit run src/app.py --server.fileWatcherType none
```

A aplicação estará disponível em `http://localhost:8501`.

## Demonstração

https://github.com/user-attachments/assets/791d40da-35ac-4784-a289-f66d2a4ef829

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
