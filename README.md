# meeting-summarizer

Ferramenta de linha de comando que busca a transcrição mais recente do Fireflies.ai, gera um resumo em português brasileiro usando Claude (Anthropic) e salva os arquivos no OneDrive e no Obsidian.

## Pré-requisitos

- Python 3.8+
- Conta no [Fireflies.ai](https://fireflies.ai) com API Key
- Conta na [Anthropic](https://console.anthropic.com) com API Key
- OneDrive instalado localmente
- Vault do Obsidian criado localmente

## Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/meeting-summarizer.git
cd meeting-summarizer
```

### 2. Crie o arquivo `.env`

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env`:

```
FIREFLIES_API_KEY=sua_chave_fireflies_aqui
ANTHROPIC_API_KEY=sua_chave_anthropic_aqui
ONEDRIVE_PATH=C:\Users\SeuUsuario\OneDrive
OBSIDIAN_PATH=C:\Users\SeuUsuario\Documents\ObsidianVault
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

## Uso

```bash
python meeting.py --client "NomeDoCliente"
```

O script irá:

1. Buscar a transcrição mais recente do Fireflies
2. Salvar a transcrição em `{ONEDRIVE_PATH}/Meetings/{NomeDoCliente}/{YYYY-MM-DD}/transcript.txt`
3. Gerar um resumo em português com Claude
4. Salvar o resumo em `{OBSIDIAN_PATH}/Meetings/{NomeDoCliente}/{YYYY-MM-DD}.md`
5. Perguntar se deseja deletar a transcrição do Fireflies

## Estrutura do resumo gerado

O arquivo `.md` salvo no Obsidian contém:

- **Resumo Geral** — visão geral da reunião
- **Decisões Tomadas** — decisões confirmadas
- **Próximos Passos / Action Items** — tarefas e responsáveis
