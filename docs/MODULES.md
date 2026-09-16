# Módulos — ERP

Documentação detalhada de cada módulo, sua responsabilidade, dependências e quem o utiliza.

---

## Backend

### `database.py`

**Responsabilidade:** Configurar conexão com SQLite e fornecer sessões de banco.

**Exports principais:**
- `engine` — motor SQLAlchemy
- `SessionLocal` — factory de sessões
- `Base` — classe base dos models
- `get_db()` — generator para dependency injection do FastAPI

**Quem usa:** `main.py`, `auth.py`, `models.py`

**Impacto de alteração:** Trocar banco (ex.: PostgreSQL) exige mudar `DATABASE_URL` e possivelmente `connect_args`.

---

### `models.py`

**Responsabilidade:** Definir entidades persistidas e relacionamentos.

| Classe | Tabela | Campos relevantes |
|--------|--------|-------------------|
| `Store` | `stores` | name, cnpj, logo_url |
| `User` | `users` | email, password, store_id |
| `Product` | `products` | name, barcode, price, stock, store_id |
| `Sale` | `sales` | total, payment_method, store_id, created_at |
| `SaleItem` | `sale_items` | sale_id, product_id, quantity, price |
| `StockMovement` | `stock_movements` | product_id, type, quantity, reason |

**Quem usa:** `main.py`, `auth.py`

**Impacto:** Qualquer mudança de coluna exige atualizar `schemas.py` e possivelmente o frontend.

---

### `schemas.py`

**Responsabilidade:** Contratos de entrada/saída da API (validação Pydantic).

**Principais schemas:**
- `ProductCreate` / `Product` — produtos
- `SaleCreate` / `Sale` / `SaleItem` — vendas
- `UserCreate` — registro
- `AddstockRequest` — entrada de estoque

**Quem usa:** `main.py` (parâmetros e `response_model`)

---

### `auth.py`

**Responsabilidade:** Segurança — hash de senha, JWT, usuário autenticado.

**Funções:**
- `hash_password` / `verify_password` — bcrypt via passlib
- `create_access_token` — JWT com expiração (60 min)
- `get_current_user` — dependency FastAPI; lança 401 se token inválido

**Quem usa:** `main.py` (Depends em endpoints protegidos)

**Depende de:** `database.get_db`, `models.User`

---

### `main.py`

**Responsabilidade:** Aplicação FastAPI — todos os endpoints e regras de negócio.

**Agrupamentos lógicos:**

| Seção | Endpoints |
|-------|-----------|
| Produtos | CRUD parcial, busca, add-stock, barcode |
| Vendas | create, list, get by id |
| Estoque | list stock-movements |
| Relatórios | summary, top products, by-payment |
| Auth | register, login, me |

**Quem chama:** Frontend via HTTP

**Depende de:** `models`, `schemas`, `database`, `auth`

---

### `check_users.py`

**Responsabilidade:** Script utilitário para listar usuários no SQLite (debug/desenvolvimento).

**Não faz parte** do fluxo da aplicação em produção.

---

## Frontend

### `main.py`

**Responsabilidade:** Bootstrap da aplicação Qt.

**Fluxo:**
1. Cria `QApplication`
2. Carrega `styles/erp.qss`
3. Exibe `LoginView`
4. Após login bem-sucedido → abre `MainWindow`

---

### `views/login_view.py` — Módulo Login

**Responsabilidade:** Tela de autenticação (email/senha).

**Chama:** `services.auth.login`

**Callback:** `on_success` → abre janela principal

---

### `views/main_window.py` — Shell da aplicação

**Responsabilidade:** Container principal com sidebar + stack de páginas.

**Instancia:**
- `DashboardView`, `PDVView`, `StockView`, `StockMovementsView`, `SalesView`

**Comportamento:** Ao trocar página, invoca `load_data()` da view ativa.

---

### `views/dashboard_view.py` — Dashboard

**Responsabilidade:** Exibir métricas de vendas.

**Dados exibidos:**
- Total vendido no período (filtro de datas)
- Tabela de produtos mais vendidos

**Chama:** `services.reports.get_sales_summary`, `get_top_products`

---

### `views/pdv_view.py` — Ponto de Venda

**Responsabilidade:** Carrinho de compras e finalização de venda.

**Funcionalidades:**
- Adicionar por código de barras ou busca por nome
- Ajustar quantidades (+/-)
- Selecionar forma de pagamento
- Imprimir cupom (opcional)
- Validar estoque localmente antes de enviar

**Chama:** `services.sales` (get_product_by_barcode, search_products, create_sale)  
**Chama:** `utils.printer.print_receipt`, `services.auth.get_me` (dados da loja no cupom)  
**Emite:** `events.sale_completed` após venda OK

---

### `views/stock_view.py` — Estoque

**Responsabilidade:** Listagem e gestão de produtos.

**Funcionalidades:**
- Listar produtos com alertas visuais (crítico ≤3, baixo ≤10)
- Cadastrar produto (`AddProductDialog`)
- Entrada manual de estoque (produto selecionado)
- Busca local por nome/código de barras

**Chama:** `services.products` (list_products, create_product, add_stock)

---

### `views/sales_view.py` — Histórico de Vendas

**Responsabilidade:** Listar vendas com filtro de data e paginação.

**Chama:** `services.sales.list_sales`

**Escuta:** `events.sale_completed` para refresh automático

---

### `views/stock_movements_view.py` — Movimentações

**Responsabilidade:** Histórico de entradas/saídas de estoque.

**Chama:** `services.stock_movements.list_stock_movements`

**Filtro:** Datas aplicadas no cliente após buscar da API

---

### `widgets/sidebar.py` — Navegação

**Responsabilidade:** Menu lateral com botões de navegação e logo da loja.

**Chama:** `services.auth.get_me` + download da `logo_url` via HTTP

---

## Camada de serviços (frontend)

### `services/api.py` — Cliente HTTP central

**Responsabilidade:** Abstração de todas as requisições HTTP.

**Funções:**
- `set_token` / `get_token` / `clear_token` — gerencia `token.txt`
- `get_headers` — monta `Authorization: Bearer`
- `api_request` — wrapper com tratamento de erro 401 e conexão

**Quem usa:** Todos os outros `services/*`

---

### `services/auth.py`

| Função | Endpoint |
|--------|----------|
| `login` | POST `/login` |
| `get_me` | GET `/me` |

---

### `services/products.py`

| Função | Endpoint |
|--------|----------|
| `list_products` | GET `/products` |
| `create_product` | POST `/products` |
| `add_stock` | POST `/products/{id}/add-stock` |

---

### `services/sales.py`

| Função | Endpoint |
|--------|----------|
| `get_product_by_barcode` | GET `/products/barcode/{barcode}` |
| `search_products` | GET `/products?search=` |
| `create_sale` | POST `/sales` |
| `list_sales` | GET `/sales` |

---

### `services/reports.py`

| Função | Endpoint |
|--------|----------|
| `get_sales_summary` | GET `/reports/sales/summary` |
| `get_top_products` | GET `/reports/products/top` |
| `get_sales_by_payment` | GET `/reports/sales/by-payment` |

---

### `services/stock_movements.py`

| Função | Endpoint |
|--------|----------|
| `list_stock_movements` | GET `/stock-movements` |

---

## Utilitários

### `utils/session.py`

Classe `Session` com campos estáticos (`access_token`, `user_id`, `store_id`) — **parcialmente utilizada**; o token efetivo está em `token.txt` via `api.py`.

### `utils/printer.py`

Impressão RAW na impressora padrão Windows (`win32print`). Usado pelo PDV para cupom não fiscal.

### `events.py`

Singleton `AppEvents` com sinal `sale_completed` para desacoplar PDV ↔ Histórico de Vendas.

### `config/settings.py`

Define `API_URL = "http://127.0.0.1:8000"` (duplicado em `services/api.py`).

---

## Matriz de dependências (quem chama quem)

```
main.py (frontend)
  └── LoginView → auth.login
  └── MainWindow
        ├── Sidebar → auth.get_me
        ├── DashboardView → reports.*
        ├── PDVView → sales.*, printer, auth.get_me, events
        ├── StockView → products.*
        ├── StockMovementsView → stock_movements.*
        └── SalesView → sales.list_sales, events

services/* → api.api_request → FastAPI (erp-backend/main.py)
main.py (backend) → models, schemas, auth, database
```

---

## Como rodar cada módulo

| Módulo | Comando | Pré-requisito |
|--------|---------|---------------|
| Backend | `uvicorn main:app --reload --host 0.0.0.0 --port 8000` (em `erp-backend/`) | Dependências Python instaladas; `--host 0.0.0.0` para o celular enviar foto |
| Frontend | `python main.py` (em `erp-frontend/`) | Backend rodando em `:8000` |
| Debug users | `python check_users.py` (em `erp-backend/`) | `erp.db` existente |
