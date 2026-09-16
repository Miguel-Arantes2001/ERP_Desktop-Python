# Visão Geral do Projeto — ERP

## Objetivo

Sistema ERP (Enterprise Resource Planning) voltado para **pequenas lojas de varejo**, com foco em:

- **Ponto de Venda (PDV)** — registrar vendas no balcão
- **Controle de estoque** — cadastro de produtos, entradas e alertas de estoque baixo
- **Histórico de vendas** — consulta e paginação por período
- **Movimentações de estoque** — rastreabilidade de entradas e saídas
- **Dashboard / relatórios** — total vendido no período e produtos mais vendidos
- **Autenticação multi-loja** — cada usuário opera apenas os dados da sua loja

O projeto serve como **portfólio de aprendizado** em arquitetura cliente-servidor, APIs REST, ORM, autenticação JWT e interfaces desktop.

---

## Estrutura do repositório

```
ERP/
├── erp-backend/          # API REST (FastAPI)
│   ├── main.py           # Endpoints e regras de negócio
│   ├── models.py         # Entidades do banco (SQLAlchemy)
│   ├── schemas.py        # Contratos de entrada/saída (Pydantic)
│   ├── database.py       # Conexão SQLite e sessão
│   ├── auth.py           # JWT, hash de senha, usuário autenticado
│   └── check_users.py    # Script utilitário (debug)
│
├── erp-frontend/         # Aplicação desktop (PySide6)
│   ├── main.py           # Ponto de entrada da UI
│   ├── views/            # Telas (login, dashboard, PDV, estoque…)
│   ├── services/         # Cliente HTTP para a API
│   ├── widgets/          # Componentes reutilizáveis (sidebar)
│   ├── utils/            # Sessão, impressão de cupom
│   ├── config/           # Configurações (URL da API)
│   ├── styles/           # Tema visual (QSS)
│   └── events.py         # Sinais Qt entre telas
│
└── docs/                 # Documentação (este diretório)
```

---

## Tecnologias

| Tecnologia | Uso |
|------------|-----|
| **Python 3** | Linguagem principal |
| **FastAPI** | Framework da API REST |
| **SQLAlchemy** | ORM e mapeamento das tabelas |
| **SQLite** | Banco de dados local (`erp.db`) |
| **Pydantic** | Validação e serialização (schemas) |
| **python-jose** | Tokens JWT |
| **passlib + bcrypt** | Hash de senhas |
| **PySide6 (Qt)** | Interface gráfica desktop |
| **requests** | Cliente HTTP no frontend |
| **pywin32** | Impressão de cupom no Windows |

---

## Módulos funcionais (alto nível)

1. **Autenticação** — registro de loja + usuário, login, token JWT
2. **Produtos / Estoque** — CRUD de produtos, entrada manual, busca por nome/código de barras
3. **Vendas (PDV)** — carrinho, formas de pagamento, baixa automática de estoque
4. **Movimentações** — histórico de entradas (`in`) e saídas (`out`)
5. **Relatórios** — resumo de vendas, top produtos, vendas por forma de pagamento
6. **Impressão** — cupom não fiscal via impressora padrão (Windows)

---

## Fluxo geral de execução

### 1. Subir o backend

```bash
cd erp-backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A API fica em `http://127.0.0.1:8000` no computador. `--host 0.0.0.0` permite o **celular na mesma Wi-Fi** abrir a página de foto (`http://SEU_IP:8000/photo/...`). Se o celular não abrir, libere a porta 8000 no firewall do Windows.

### 2. Subir o frontend

```bash
cd erp-frontend
python main.py
```

### 3. Fluxo do usuário

```
Login → Token salvo em token.txt → MainWindow (sidebar + telas)
         ↓
    Dashboard | PDV | Estoque | Movimentações | Vendas
         ↓
    Todas as requisições usam Authorization: Bearer <token>
         ↓
    Backend filtra dados por store_id do usuário logado
```

### 4. Fluxo de uma venda (PDV)

1. Operador busca produto (código de barras ou nome)
2. Monta carrinho na tela (`PDVView`)
3. Frontend envia `POST /sales` com itens e forma de pagamento
4. Backend valida estoque, baixa quantidade, cria `Sale`, `SaleItem` e `StockMovement` (tipo `out`)
5. Opcionalmente imprime cupom e emite sinal `sale_completed` para atualizar a tela de vendas

---

## Entidades principais do banco

| Entidade | Descrição |
|----------|-----------|
| `Store` | Loja (nome, CNPJ, logo) |
| `User` | Usuário vinculado a uma loja |
| `Product` | Produto com preço, estoque e código de barras |
| `Sale` | Venda (total, forma de pagamento, data) |
| `SaleItem` | Item de uma venda (produto, quantidade, preço) |
| `StockMovement` | Movimentação de estoque (entrada/saída, motivo) |

---

## Pontos de atenção (para evolução futura)

- Não há `requirements.txt` na raiz — dependências devem ser documentadas/instaladas manualmente
- `SECRET_KEY` está hardcoded em `auth.py` (inadequado para produção)
- Token persistido em arquivo local (`token.txt`)
- Pasta `static/` referenciada no backend pode não existir ainda
- Impressão depende de Windows (`win32print`)
