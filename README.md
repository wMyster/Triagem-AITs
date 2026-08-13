# 🚦 Triagem AIT — Sistema Integrado de Triagem, Controle e Remessa de AITs

[![Versão](https://img.shields.io/badge/vers%C3%A3o-1.2.0-blue.svg)](https://github.com/wMyster/Triagem-AITs)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-orange.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Banco_de_Dados-SQLite_WAL-skyblue.svg)](https://www.sqlite.org/)

O **Triagem AIT** é uma solução corporativa completa desenvolvida para automatizar e centralizar o ciclo de vida operacional dos Autos de Infração de Trânsito (AITs) emitidos por Agentes de Trânsito e pela Guarda Civil Municipal (GCM).

O sistema substituiu planilhas paralelas do Excel e bancos do MS Access por uma plataforma web moderna, multi-máquina, resiliente a concorrência em rede e auditada.

---

## 🌟 Principais Funcionalidades

### 1. 🛡️ Segurança e Controle de Acesso (RBAC)
- **Autenticação Individual**: Acesso controlado por usuário e senha com criptografia forte (`pbkdf2:sha256`).
- **Perfis de Acesso Segregados**:
  - `transporte`: Digitação rápida, recebimento de AITs, distribuição de talões e criação de remessas.
  - `dct`: Conferência em lote, emissão de termos oficiais, transferências de saldos, tratamento de divergências e auditoria.
  - `empresa`: Portal restrito da Empresa de Processamento para conferência individual item a item.
  - `consulta`: Acesso somente leitura para relatórios operacionais e consultas.
  - `admin`: Controle total, gestão de usuários e correções auditadas com justificativa.

### 2. 📚 Distribuição e Gerenciamento de Talões (50 Folhas)
- **Geração Automática**: Cadastro do talão (nº inicial ao nº final) validando a faixa e gerando automaticamente os 50 AITs esperados vinculados ao servidor.
- **Redistribuição de Saldos**: Módulo para transferência de AITs pendentes entre servidores com preservação do histórico de entrega original.

### 3. ⏳ Controle Sequencial e Diagnóstico de Faltantes
- **Identificação Automática de Omissões**: Mapeamento em tempo real dos AITs esperados que ainda não deram entrada no setor.
- **Métricas de Atraso**: Exibição dos dias decorridos desde a entrega do talão para subsidiar cobranças operacionais.

### 4. 📦 Remessas Eletrônicas e Portal da Empresa de Processamento
- **Agrupamento Automático**: Criação de Remessas Eletrônicas numeradas (`REM-2026/001`) para acompanhamento do envio físico dos documentos.
- **Conferência Estrita Item a Item**: Exigência de conferência individual por documento pela empresa contratada (sem aprovação em lote cega).
- **Suporte Nativo a Código de Barras**: Leitura instantânea por scanners leitores de código de barras USB/Wireless com avanço automático.
- **Gestão de Divergências**: Registro de inconsistências (`Não Localizado`, `Ilegível`, `Danificado`) com fluxo de resolução pelo setor DCT.

### 5. 🌐 Monitoramento do Status de Rede em Tempo Real (v1.2)
- **Header Badge Dinâmico**: Pill visual LED no topo da tela exibindo a latência e a integridade da conexão com a pasta compartilhada de rede `G:\Triagem AITs\triagem_ait.db`.
- **Trava de Segurança Antidesalinhamento**: Em caso de queda de rede, exibe um banner de alerta e pausa temporariamente o envio de formulários até a reconexão.

### 6. 📜 Trilha de Auditoria Imutável (Logs)
- Registro imutável de todas as ações de inclusão, alteração, exclusão, transferência e conferência com usuário, perfil, data/hora e justificativa.

---

## ⚙️ Como Executar o Projeto

### Pré-requisitos
- Python 3.10 ou superior instalado.

### 1. Clonar o Repositório
```bash
git clone https://github.com/wMyster/Triagem-AITs.git
cd Triagem-AITs
```

### 2. Criar e Ativar o Ambiente Virtual
```bash
python -m venv venv
# No Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Executar a Migração de Banco de Dados
```bash
python scripts/migrate_v3.py
```

### 5. Iniciar o Servidor Web Local
```bash
python app.py
```
Acesse o sistema no seu navegador através do endereço: `http://localhost:5000`

---

## 🔑 Credenciais Atualizadas de Acesso

| Usuário | Senha | Setor / Perfil | Atribuição |
| :--- | :--- | :--- | :--- |
| `transporte` | `triagem123!` | Módulo Triagem | Recebimento de AITs, Cadastro de Talões e Remessas |
| `dct` | `dct123!` | Módulo DCT | Conferência em Lote, Transferências e Auditoria |
| `empresa` | `empresa123!` | Empresa Processamento | Portal de Conferência Individual de Remessas |
| `admin` | `admin123!` | Administrador | Gestão Total do Sistema e Usuários |
| `consulta` | `consulta123!` | Consulta | Visualização de Relatórios (Somente Leitura) |

---

## 🖥️ Implantação em Rede (Múltiplas Estações)

Para operar o sistema em 4 ou mais máquinas conectadas em rede local:
1. Certifique-se de que a pasta compartilhada `G:\Triagem AITs` está mapeada em todas as máquinas com permissão de leitura/escrita.
2. O sistema detectará automaticamente a presença da pasta `G:\Triagem AITs\triagem_ait.db` e ativará o modo **WAL (Write-Ahead Logging)** do SQLite com resiliência a travamentos de rede.

---

## 📦 Compilação para Executável (.EXE)

Para compilar o projeto em um executável autônomo para Windows com suporte ao Tray Icon e Google Chrome:
```bash
pyinstaller triagem_ait.spec --noconfirm
```
O executável compilado será gerado na pasta `dist/triagem_ait.exe`.

---

## 📄 Licença e Uso

Desenvolvido para o **Setor de Triagem e Estatística de Trânsito** &copy; 2026. Todos os direitos reservados.
