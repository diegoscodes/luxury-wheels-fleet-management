# 🚗 Luxury Wheels - Sistema de Gestão de Frota

Este projeto é um sistema completo de gerenciamento de frota veicular desenvolvido com **Python**, **Flask** e **SQLite**, permitindo o controle de veículos, clientes, reservas, pagamentos, manutenções e alertas automáticos.

---

## 🔧 Funcionalidades Implementadas

✅ Autenticação com login e logout  
✅ Cadastro, edição e exclusão de veículos  
✅ Visualização de imagem do veículo (com galeria)  
✅ Controle de status (Disponível, Alugado, Em manutenção)  
✅ Alertas de revisão vencida ou próxima (até 5 dias)  
✅ Envio de e-mails automáticos com alertas de revisão  
✅ Cadastro de clientes e reservas  
✅ Registro e controle de pagamentos com filtros e exportação  
✅ Relatórios exportáveis em Excel (manutenções e pagamentos)  
✅ Dashboard com indicadores e gráficos  
✅ Design responsivo com Bootstrap

---

## 🗂️ Estrutura do Projeto

```
luxurywheels_fleet/
├── app.py
├── database.py
├── luxurywheels.db
├── atualizar_imagens.py
├── static/
│   └── imagens/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── vehicles.html
│   ├── exibir_imagem.html
│   └── ...
├── entrega_final/
│   ├── README.md
│   └── prints/
│       ├── 01_login.png
│       ├── 02_dashboard.png
│       └── ...
└── .venv/
```

---

## 💻 Como Executar

1. **Ativar o ambiente virtual**:

   No PowerShell:
   ```bash
   .\.venv\Scripts\activate
   ```

2. **Executar o sistema**:

   ```bash
   python app.py
   ```

3. **Acessar no navegador**:

   ```
   http://127.0.0.1:5001
   ```

---

## 🧪 Prints para entrega (em `/entrega_final/prints/`)

- 01_login.png → Tela de login
- 02_dashboard.png → Página inicial com alertas
- 03_veiculos.png → Tabela de veículos
- 04_veiculo_imagem.png → Imagem do veículo ao clicar no modelo
- 05_add_veiculo.png → Formulário de cadastro
- 06_editar_veiculo.png → Tela de edição de veículo
- 07_clientes.png → Listagem de clientes
- 08_reservas.png → Listagem de reservas
- 09_pagamentos.png → Listagem e filtros de pagamentos
- 10_relatorio_manutencao.png → Tela de geração de relatório Excel

---

## 📦 Requisitos Técnicos

- Python 3.11+
- Flask
- Flask-Mail
- Pandas
- openpyxl
- matplotlib

Instale os pacotes com:

```bash
pip install -r requirements.txt
```

---

## 👨‍💻 Desenvolvido por

**Diego [Seu Sobrenome Aqui]**  
Projeto Final – Curso Python – Tókio School  
Ano: 2025
