# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup e Comandos

```bash
# Ambiente
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Banco de dados
python manage.py migrate

# Servidor de desenvolvimento
python manage.py runserver

# Testes
python manage.py test                                  # todos
python manage.py test finance.tests.EntryTests         # módulo específico
```

## Estrutura Django (planejada)

- `core/` — autenticação, layout base, dashboard, aprovação de usuários
- `finance/` — models: `Category`, `Entry`, `Param`, `Fact`; views dos módulos principais
- `templates/` — `base.html` com sidebar/footer; partials carregados via HTMX para modais
- `Ddl_Bdhpbtecdev_Sqlite.sql` — DDL de referência do banco (adaptado com campos de Soft Delete)

## Decisões Arquiteturais Chave

- **Soft Delete:** `categories` e `entries` nunca recebem `DELETE` direto — usar `is_deleted=True`.
- **Saldo cumulativo:** calculado via **Window Functions** no ORM do Django, não em Python.
- **Interações dinâmicas:** todo dinamismo de UI (modais, buscas, paginação, autocompletar) via **HTMX** — sem jQuery ou JS verbose.
- **Data base (`agora`):** lida da tabela `params` onde `label = 'agora'`; fallback para data atual.

---

# Especificação do Sistema de Controle Financeiro

## 1. Visão Geral
Sistema de controle financeiro a ser desenvolvido em **Django**, utilizando banco de dados **SQLite** e estilizado com **Tailwind CSS**. O sistema será focado em gerenciar receitas e despesas (lançamentos), categorizá-los e apresentar um dashboard gerencial.

## 2. Requisitos Não Funcionais e Arquitetura
*   **Framework Backend:** Django.
*   **Banco de Dados:** SQLite (com base no script de DDL `Ddl_Bdhpbtecdev_Sqlite.sql` fornecido, adaptado para suportar Soft Delete).
*   **Interface (Frontend):** Tailwind CSS, com implementação de Tema Escuro (Dark Mode).
*   **Dinamismo no Frontend:** Utilização obrigatória de **HTMX** para interações dinâmicas (como modais, buscas e paginação), dispensando o uso de jQuery ou código JavaScript verboso. O HTMX fará a comunicação fluida nativamente com o Django.
*   **Comportamento de Listagem:** Paginação de 25 em 25 itens, contendo também a opção "Listar todos".

## 3. Autenticação e Autorização
*   **Registro:** Na criação de conta, o sistema deve solicitar: `Username`, `Password` e `E-mail`.
*   **Aprovação Inteligente (via Django nativo):**
    *   Novos usuários serão registrados com a flag nativa do Django `is_active=False`.
    *   A tentativa de login por um usuário inativo deve ser bloqueada exibindo a mensagem: *"Aguardando aprovação"*.
*   **Área do Administrador:**
    *   Na tela inicial (Dashboard) do Admin, exibir uma listagem de usuários inativos (`is_active=False`).
    *   O Administrador deve poder aprovar o usuário (alterando a flag para `is_active=True`) com apenas 1 clique via requisição HTMX.
    *   Uma vez aprovado, o usuário some da lista. Se a lista estiver vazia (sem pendências), ela não deve ser renderizada na tela.

## 4. Interface do Usuário (UI/UX)
*   **Layout:** Tema Escuro (Dark Mode).
*   **Navegação (Sidebar):**
    *   Localizada no lado esquerdo da tela.
    *   Deve conter os links para os módulos do sistema, utilizando ícones visuais para cada opção.
    *   Deve possuir um botão/ícone de "Toggle" para recolher e expandir o menu lateral.
*   **Rodapé (Footer):**
    *   Exibir o nome do usuário (`username`) atualmente logado.
    *   Conter um botão/ícone lateral para efetuar o logout do sistema.
*   **Comportamento de Formulários (Modais Integrados):**
    *   Criações, edições e confirmações de exclusão de registros deverão ser feitas através de Modais carregados de forma assíncrona com HTMX, mantendo o usuário sempre na tela de listagem para uma experiência fluida (Single Page App-like).

---

## 5. Módulos e Funcionalidades

### 5.1 Dashboard (Página Inicial)
*   Exibição do gráfico de barras contemplando os valores totais de **créditos** e **débitos** por mês do ano corrente.
*   *Nota técnica:* A obtenção do ano corrente pode ser feita via consulta SQL `SELECT strftime('%Y', 'now');`.
*   Painel de aprovação rápida de usuários (visível apenas para admins, se houver pendências).

### 5.2 Parâmetros (`params`)
*   **Listagem:** Colunas: `id`, `name`, `type`.
*   **Busca:** Permitir pesquisa por texto livre nas strings ou busca exata pelo `id`.
*   **Ações (em cada linha):**
    *   **Criar/Editar:** Abrir modal com os campos e botões "Salvar" e "Cancelar".
    *   **Excluir:** Exibir modal de confirmação antes de deletar.

### 5.3 Categorias (`categories`)
*   **Listagem:** Colunas: `id`, `label`, `value`, `default`.
*   **Busca:** Permitir pesquisa por texto nas strings ou busca pelo `id`.
*   **Ações (em cada linha):**
    *   **Criar/Editar:** Abrir modal.
    *   **Excluir (Deleção Lógica / Soft Delete):** Exibir modal de confirmação. A exclusão não efetuará um "DELETE" direto no banco de dados, mas sim atualizará um campo de auditoria (ex: `is_deleted=True`).
    *   *Regra de Validação:* A ação de exclusão só deve estar disponível se a categoria **não** possuir vínculos nas tabelas `entries` ou `facts`.

### 5.4 Lançamentos (`entries`)
*   **Segurança Financeira (Soft Delete):** Adotar o padrão de "Deleção Lógica" também nos lançamentos, garantindo rastreabilidade do histórico financeiro.
*   **Cálculo de "Saldo Anterior" (Card Resumo no Topo):**
    *   Verificar o registro na tabela `params` onde `label = 'agora'`. O campo `value` deve conter uma data base. Caso não exista, utilizar a **data atual**.
    *   Calcular o somatório financeiro: Somar todos os campos `vl_entry` de `entries` que possuam `status = 1` E `dt_entry <= data_base`.
    *   **Regra de Exibição:** Para não prejudicar a paginação e evitar falhas visuais, este "Saldo Anterior" não será simulado como a primeira linha da tabela. Ele será exibido em um **Card de Destaque** acima da tabela de listagens, sinalizando claramente a Data Base e o valor do saldo computado até ali.
*   **Listagem (Movimentações):**
    *   Filtro base da listagem buscará registros com `dt_entry > data_base` (ordenação `dt_entry` ASC).
    *   **Colunas:**
        *   **Ações:** Ícones de edição e exclusão.
        *   **Dia da semana:** Calculado a partir de `entries.dt_entry`.
        *   **Data:** `entries.dt_entry` no formato dd/mm/yyyy.
        *   **Grupo:** `entries.ds_subcategory`.
        *   **Descrição:** `entries.ds_category`.
        *   **Categoria:** Nome da categoria associada (`categories.name`).
        *   **Valor:** `entries.vl_entry`.
        *   **Total (Saldo Cumulativo):** Somatório progressivo calculando a partir do Card de "Saldo Anterior" +/- o `vl_entry` da linha atual. *Diretriz de Performance: Este cálculo linha a linha deverá ser feito de forma nativa no banco de dados utilizando **Window Functions** via ORM do Django.*
        *   **Regra Visual (Cores):** Os campos **Valor** e **Total** (incluindo o Card de Saldo Anterior) devem ser exibidos na cor **verde** para valores positivos (>= 0) e na cor **vermelha** para valores negativos (< 0).
*   **Ações (em cada linha):**
    *   **Criar/Editar:** Abrir modal.
    *   **Excluir:** Exibir modal de confirmação. Só será permitida se o registro **não** possuir vínculo na tabela `facts`.
*   **Formulários de Criação (New Entry) e Edição (Update Entry):**
    *   **Campos principais:** `Category` (obrigatório, listar em ordem alfabética), `Description` (obrigatório), `Sub Desc.` (opcional), `Details` (opcional, textarea), `Date` (obrigatório, com calendário e padrão de data atual se vazio), `Vl. Entry` (obrigatório, duas casas decimais, aceita negativos).
    *   **Flags (Checkboxes):** `Status`, `Fixed`, `Checked`, `Published` (valores booleanos 0 ou 1).
    *   **Dinâmica:** Ao selecionar uma Categoria no modo de Criação, buscar o último registro dessa categoria e autocompletar "Description" e "Sub Desc." automaticamente.

### 5.5 Parcelamentos (Tela Times)
*   Módulo focado na geração rápida e em lote de lançamentos parcelados, como faturas de cartão de crédito.
*   **Formulário de Regras:**
    *   **Parcelas:** Dropdown de 2 a 12 (padrão: 2).
    *   **Cartões:** Dropdown com bandeiras/tipos ("Mastercard", "Visa", "Hering", "Crédito", "Débito"). Ao selecionar, o campo **Dia** (vencimento) é alterado automaticamente (ex: Mastercard = 15, Visa = 8, Crédito/Débito = 0).
    *   **Mês/Ano de Início:** Dropdowns com base na data atual para projeção dos vencimentos.
    *   **Categoria e Descrição:** Funcionamento semelhante à criação de lançamento normal (com autocompletar na seleção da categoria).
    *   **Valores:** Campos de "Valor Total" e "Valor Parcela" interligados (Botão "Total" para calcular Valor Total a partir da parcela * quantidade).
*   **Geração (Prévia e Salvamento):**
    *   **Botão "Gerar Parcela":** Cria uma tabela prévia das parcelas com Vencimento calculado, incrementando meses (e anos quando necessário).
    *   **Ajuste de Centavos:** O sistema rateará as parcelas (Valor Total / Parcelas) e garantirá que eventuais diferenças de centavos sejam aplicadas nas últimas parcelas para bater exatamente com o Valor Total.
    *   **Salvar (Save Changes):** Grava os múltiplos registros na tabela `entries`, concatenando a descrição da parcela no formato `Descrição (X de Y)`.

### 5.6 Manutenção em Lote (Tela Support)
*   Interface voltada à filtragem e ações massivas nos registros.
*   **Filtros:** `entries.ds_category` (descrição) e `category.name` (nome da categoria).
*   **Listagem Editável:** Exibe colunas como Data, Grupo, Descrição, Categoria e Valor.
    *   Permite a **edição inline** de todos os campos listados de forma direta.
    *   Possui checkbox geral de "Selecionar Todos" e seleção individual por linha.
*   **Ações em Lote (Perform Action):**
    *   A partir de um Dropdown selecionado ("Update", "Delete", "Copy"), aplica a ação a todos os registros marcados na listagem.

### 5.7 Visão por Cartões / Faturas (Tela Cards)
*   Visão específica para acompanhar o fechamento e lançamentos agrupados por fatura de cartão.
*   **Navegação Temporal:** Controles com setas (Esquerda/Direita) para recuar ou avançar meses/anos.
*   **Filtro Rápido:** Botões dinâmicos gerados no padrão "Bandeira YYYY/MM" (ex: "Mastercard 2026/01", "Visa 2026/01"). O clique no botão aplica o filtro de `ds_subcategory` = Bandeira e o período exato (Mês/Ano).
*   **Listagem Específica:**
    *   Ordenação obrigatória por `vl_entry` do maior para o menor.
    *   Colunas exibidas: Ações (Editar/Excluir via modais), Dia da Semana, Data, Grupo, Descrição, Categoria, Valor e **Total (Saldo cumulativo da lista filtrada)**.

---

## 6. Sugestões de Melhoria e Otimização Técnica (UX/HTMX)
*   **Interatividade HTMX Dinâmica:** Nas telas de Formulários (New Entry / Times), em vez de criar lógicas em JavaScript puro para atualizar campos relacionados, pode-se usar HTMX disparando gatilhos em `change`. Por exemplo, alterar a `Category` envia uma requisição `hx-get` ou `hx-post` ao Django, que devolve os dados para autocompletar os campos `Description` e `Sub Desc.` rapidamente.
*   **Cálculo de Parcelas Centralizado no Backend:** Na tela **Times**, o fluxo de iteração de meses, verificação de ano bissexto/dias finais e, principalmente, a distribuição dos centavos do rateio na última parcela, deve ser uma inteligência concentrada em uma view Django. Ao clicar em "Gerar Parcela", o HTMX consulta o backend, que devolve o HTML da tabela já calculada pronta para conferência do usuário.
*   **Edição e Ações Inline Eficientes (Tela Support):** A funcionalidade "Support" se encaixa no design pattern de "Bulk Update". Usando HTMX, as ações de Update, Copy ou Delete podem enviar um form apenas com os checkboxes selecionados, aplicando as regras sem reload na página, ou ainda salvando alterações inline conforme os inputs perdem foco (blur).
*   **Transições Fluídas na Navegação (Tela Cards):** Ao retroceder e avançar nos meses da tela Cards, um componente HTMX `hx-target` pode substituir apenas os dados da tabela e os próprios rótulos dos botões, sem recarregar menus e barras laterais, dando o aspecto de "Single Page Application".
