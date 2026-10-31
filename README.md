# LeadForge Prompt Evaluator

Avaliação quantitativa de prompts para qualificação de leads no LeadForge.

## Pergunta mensurável
Qual variante de prompt gera classificação mais consistente, com menor custo e latência?

## O que ele prova
- Entendimento de **avaliação de LLMs**
- Métricas: latência, custo estimado, taxa de aprovação/rejeição, consistência entre runs
- Reprodutibilidade: script único gera CSV de resultados

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Dados
Usamos `data/sample_leads.json` com leads sanitizados (sem dados reais de pessoas).

## Executar
```bash
# Define a variável de modelo desejada
export MODEL_DEFAULT="gpt-4o-mini"
export MODEL_FALLBACK="gpt-4o-mini"

# Executa experimento
python -m leadforge_prompt_evaluator.cli
```

## Output
- `runs/latest.csv` — resultados por lead/prompt
- `runs/summary.csv` — agregado por variante

## Critérios de sucesso
- [x] Script roda end-to-end
- [x] CSV reprodutível
- [x] Métricas claras
- [x] README com comandos exatos
