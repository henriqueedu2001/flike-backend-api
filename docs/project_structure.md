# Estrutura do repositório

```
project_root/
│
├── app/
│   ├── __init__.py
│   │
│   ├── main.py                # entrypoint da API
│   │
│   ├── api/                  # camada de endpoints (FastAPI)
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── predict.py
│   │
│   ├── services/             # lógica de aplicação (orquestra módulos)
│   │   ├── __init__.py
│   │   └── prediction_service.py
│   │
│   ├── modules/              # módulos independentes (ML, processamento)
│   │   ├── __init__.py
│   │   ├── model.py
│   │   └── preprocessing.py
│   │
│   └── schemas/              # Pydantic (entrada/saída)
│       ├── __init__.py
│       └── prediction_schema.py
│
├── tests/
│   ├── __init__.py
│   ├── test_model.py
│   └── test_preprocessing.py
│
├── pyproject.toml  (ou requirements.txt)
└── README.md
```



# Ideia central da arquitetura

Separação clara:

| Camada     | Responsabilidade          |
| - | - |
| `api`      | HTTP / FastAPI            |
| `services` | orquestra lógica          |
| `modules`  | lógica pura (ML, funções) |
| `schemas`  | contratos de dados        |

 Regra de ouro:

> `api → services → modules` (fluxo único, sem voltar)



# 1. Módulos (executáveis isoladamente)

## `app/modules/model.py`

```python
def predict(data: list[float]) -> float:
    # Simulação de modelo
    return sum(data) / len(data)


if __name__ == '__main__':
    # Executável isoladamente
    sample = [1.0, 2.0, 3.0]
    result = predict(sample)
    print(f'Result: {result}')
```

Pode rodar direto:

```bash
python -m app.modules.model
```



## `app/modules/preprocessing.py`

```python
def normalize(data: list[float]) -> list[float]:
    total = sum(data)
    return [x / total for x in data]
```



# 2. Services (orquestração)

## `app/services/prediction_service.py`

```python
from app.modules.model import predict
from app.modules.preprocessing import normalize


def run_prediction(data: list[float]) -> float:
    processed = normalize(data)
    return predict(processed)
```

Aqui você conecta os módulos — **mas ainda testável isoladamente**.



# 3. API (FastAPI desacoplada)

## `app/api/routes/predict.py`

```python
from fastapi import APIRouter
from app.schemas.prediction_schema import PredictionRequest, PredictionResponse
from app.services.prediction_service import run_prediction

router = APIRouter()


@router.post('/predict', response_model=PredictionResponse)
def predict_endpoint(request: PredictionRequest):
    result = run_prediction(request.data)
    return PredictionResponse(result=result)
```

✔️ Endpoint não sabe nada de ML — só chama service.



# 4. Entry point da API

## `app/main.py`

```python
from fastapi import FastAPI
from app.api.routes import predict

app = FastAPI()

app.include_router(predict.router)
```



# 5. Schemas (Pydantic)

## `app/schemas/prediction_schema.py`

```python
from pydantic import BaseModel


class PredictionRequest(BaseModel):
    data: list[float]


class PredictionResponse(BaseModel):
    result: float
```



# 6. Testes independentes

## `tests/test_model.py`

```python
from app.modules.model import predict


def test_predict():
    data = [1, 2, 3]
    result = predict(data)
    assert result == 2.0
```



## `tests/test_preprocessing.py`

```python
from app.modules.preprocessing import normalize


def test_normalize():
    data = [1, 1, 2]
    result = normalize(data)
    assert sum(result) == 1.0
```



# COMO EVITAR PROBLEMAS DE IMPORT (ESSENCIAL)

## Regra mais importante:

> **Sempre use imports absolutos a partir de `app`**

```python
# correto
from app.modules.model import predict

# errado
from modules.model import predict
```



## ✅ Execute sempre a partir da raiz do projeto

```bash
cd project_root
pytest
uvicorn app.main:app --reload
```



## ✅ Para rodar módulo isolado

```bash
python -m app.modules.model
```

👉 Isso evita erro clássico de import relativo quebrado.



## ✅ Todo diretório precisa de `__init__.py`

Mesmo vazio:

```
touch app/__init__.py
touch app/modules/__init__.py
...
```



# 💡 Dica avançada (opcional, mas poderosa)

Se quiser garantir ainda mais robustez:

## `pyproject.toml`

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

Ou use:

```bash
export PYTHONPATH=.
```



# 🧭 Resumo da filosofia

* `modules/` → código puro (reutilizável, executável)
* `services/` → coordena módulos
* `api/` → só interface HTTP
* imports absolutos (`app.*`)
* execução via `-m`



# ⚠️ Erros comuns que essa estrutura evita

* ❌ `ModuleNotFoundError`
* ❌ imports relativos quebrando (`..module`)
* ❌ código impossível de testar fora da API
* ❌ lógica acoplada ao FastAPI