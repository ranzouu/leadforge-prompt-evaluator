# LeadForge Prompt Evaluator

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![scikit-learn](https://img.shields.io/badge/scikit-learn-1.5%2B-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production-brightgreen)

Avaliação quantitativa e reprodutível de prompts para qualificação de leads no **LeadForge**. Compare variantes de prompt por consistência, custo e latência — com suporte a modo demo sem API key.

## Sobre

- **3 variantes de prompt** para classificação de leads (`quente / morno / frio`)
- **Métricas comparáveis**: latência, tokens de entrada/saída, taxa de aprovação/rejeição e distribuição de labels
- **Modo demo** com respostas fixas para testar o fluxo end-to-end sem gastar créditos
- **Saídas CSV** prontas para análise: `runs/latest.csv` e `runs/summary.csv`
- **CLI enxuta** com entrada por variáveis de ambiente

## Stack

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.11+ |
| HTTP | httpx + tenacity |
| Dados | pandas |
| CLI/Terminal | rich |
| Testes | pytest |

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Como rodar

### Modo demo (sem API key)

```bash
python -m leadforge_prompt_evaluator
```

### Modo produção

```bash
export LLM_API_KEY="sua-chave"
export LLM_BASE_URL="https://api.openai.com/v1"
export MODEL_DEFAULT="gpt-4o-mini"
export MODEL_FALLBACK="gpt-4o-mini"
python -m leadforge_prompt_evaluator
```

## Métricas geradas

Cada run registra latência, tokens, label, confidence e reasoning. O `runs/summary.csv` agrega por variante: runs, erros, taxa de classificação, latência média e labels observadas.

## Resultados da rodada real (10/nov/2026 — `openai/gpt-oss-20b` via Groq)

36 chamadas reais (12 leads × 3 variantes), sem erros. Dados completos em `runs/latest.csv`.

| Variante | Rótulos extraídos | Labels vistos | Leitura |
|---|---|---|---|
| `v1_short` | **4/12** | só `frio` | modelo de raciocínio **recusa** em 8/12 ("preciso de mais informações") — prompt sem formato não sustenta classificação |
| `v2_structured` | **12/12** | `frio`/`morno`/`quente` | **vencedor**: schema explícito + tolera bloco ```json na resposta |
| `v3_criteria` | **8/12** | `None`/`fit_unknown`/`unknown` | **drift de vocabulário**: o prompt não fixa o enum, o modelo inventa valores fora de `quente/morno/frio` |

Latência real: 367–2164 ms (média ~920 ms), ~240 tokens de saída por chamada.

**Bugs de integração que o harness pegou no caminho** (e que motivaram os fixes em `experiment.py`):

1. Rodada inicial com `openai/gpt-oss-20b` + `max_tokens=200`: 5 erros 429 (sem retry) e **respostas vazias** — o canal de pensamento do modelo de raciocínio comia o budget antes da resposta. Fix: `MAX_TOKENS=1000` (padrão), retry com backoff (5s/15s) e pacing de 2s respeitando 30 RPM do free tier.
2. Modelo legado: `llama-3.1-8b-instant` foi desligado do free tier da Groq em 16/ago/2026 — o script de rodada descobre os modelos disponíveis na chave.

Space público com a comparação: [`ranzouu/prompt-evaluator`](https://ranzouu-prompt-evaluator.static.hf.space).

## Variantes avaliadas

| Variante | Estilo | Saída |
|----------|--------|-------|
| `v1_short` | Classificação curta | Texto puro |
| `v2_structured` | Com campos nomeados | JSON estruturado |
| `v3_criteria` | Critérios de fit B2B | JSON com reasoning |

## Exemplos de uso

```python
from leadforge_prompt_evaluator.experiment import run_experiment, save_runs

runs = run_experiment(models=["gpt-4o-mini"])
latest_path, summary_path = save_runs(runs)
```

## Testes

```bash
pytest -q
```

## Licença

MIT
