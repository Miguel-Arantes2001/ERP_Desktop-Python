# ERP Desktop para Pequenas Lojas 🏪

Este projeto é um **ERP Desktop desenvolvido em Python**, projetado para atender **pequenas lojas** que precisam de controle de vendas, estoque e usuários, sem depender de internet e sem a complexidade de sistemas corporativos.

O sistema foi concebido com **arquitetura profissional**, utilizando **FastAPI como backend** e **PySide6 (Qt) como frontend desktop**, seguindo o modelo **cliente-servidor local**, com foco em segurança, organização e possibilidade de crescimento.

---

## 🎯 Problema que o projeto resolve

Pequenos comércios frequentemente enfrentam problemas como:
- Controle manual ou via planilhas
- Sistemas online caros ou complexos
- Dependência de internet
- Falta de separação entre usuários e dados

Este ERP resolve esses problemas oferecendo:
- Controle de vendas (PDV)
- Controle de estoque
- Gestão de usuários com autenticação
- Operação **offline**
- Isolamento de dados por loja (multi-tenant)

Tudo em um sistema:
- Leve
- Local
- Simples de operar
- Pensado para o contexto real de pequenas lojas

---

## 🧠 Conceito e Arquitetura

O projeto foi pensado **além do código**, abordando arquitetura, segurança e escalabilidade.

### Arquitetura Geral

Frontend Desktop (PySide6)
↓ HTTP / JSON
Backend Local (FastAPI)
↓
Banco de Dados (SQLite por loja)


### Principais decisões arquiteturais

- O frontend **não acessa o banco de dados diretamente**
- Todas as regras de negócio passam pelo backend
- Comunicação via **API REST**
- Arquitetura preparada para crescimento futuro (cloud, multi-loja, relatórios)

---

## 🔐 Autenticação e Segurança

O sistema implementa **autenticação baseada em JWT (JSON Web Token)**:

- Login gera um **token de acesso**
- Token é enviado em cada requisição autenticada
- Backend valida permissões e identidade do usuário
- Evita acesso não autorizado aos dados

Essa abordagem replica padrões usados em sistemas web modernos, mesmo sendo um aplicativo desktop.

---

## 🧩 Backend (FastAPI)

Responsável por:
- Regras de negócio
- Autenticação e validação de usuários
- Emissão e validação de tokens JWT
- Controle de estoque
- Registro de vendas
- Comunicação com o banco de dados

Conceitos aplicados:
- Endpoints REST (`GET`, `POST`)
- Separação por camadas (routes, services, models)
- Validações centralizadas
- Testes via Swagger (OpenAPI)

---

## 🖥️ Frontend (PySide6 / Qt)

Responsável por:
- Interface gráfica
- Fluxo de PDV
- Experiência do usuário
- Consumo da API via requisições HTTP autenticadas

Características:
- Interface desktop nativa
- Componentes reutilizáveis
- Estilo visual centralizado (QSS)
- Foco em usabilidade para operação diária

---

## 🏬 Arquitetura Multi-Tenant

O sistema foi projetado como **multi-tenant**, onde:

- Cada loja possui **login próprio**
- Cada loja utiliza **seu próprio banco de dados SQLite**
- Os dados são completamente isolados
- Um erro ou crescimento de uma loja não afeta as demais

Essa abordagem aumenta:
- Segurança
- Organização
- Escalabilidade
- Facilidade de manutenção

---

## 🗄️ Banco de Dados

- **SQLite**
- Banco local, leve e confiável
- Ideal para pequenas lojas
- Suporta milhares de registros sem perda de performance
- Fácil backup e migração futura

---

## 🚀 Possibilidades de Evolução

A arquitetura permite evolução para:
- Banco centralizado (PostgreSQL / MySQL)
- Backend em nuvem
- Multi-lojas em rede
- Relatórios avançados
- Dashboards analíticos
- API pública

---

## 🛠️ Stack Tecnológica

- Python
- FastAPI
- PySide6 (Qt)
- SQLite
- JWT (Autenticação)
- HTTP / REST
- JSON

---

## 📌 Considerações Finais

Este projeto representa um **estudo completo de desenvolvimento de software**, cobrindo desde a concepção, decisões arquiteturais, segurança, até a implementação prática.

Mais do que um ERP funcional, é um projeto focado em **boas práticas, arquitetura limpa e visão de produto**, alinhado a cenários reais de mercado.

📄 Projeto desenvolvido para fins educacionais e demonstração técnica.
