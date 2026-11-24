# Manual Técnico — Cortamato

**Sistema de gestão de corta-mato escolar**

Projeto Integrador — PSI/RC — 2026/2027

Agrupamento de Escolas de Padre Benjamim Salgado

## 1. Objetivo do manual

Este manual documenta a instalação, configuração, arquitetura, utilização, manutenção e testes da aplicação Cortamato.

O sistema centraliza provas escolares, turmas, alunos, inscrições, dorsais, chegadas, classificações, escalões e apuramentos numa base de dados MySQL ou MariaDB.

## 2. Estrutura do projeto

```text
Cortamato
├── main.py
├── requirements.txt
├── README.md
├── Controllers/
├── Model/
├── View/
├── SQL/
├── tests/
└── docs/
```

### 2.1 Arquitetura MVC

- **Model**: classes de dados e operações de leitura/escrita na base de dados.
- **View**: interfaces Flet e componentes de apresentação.
- **Controller**: coordenação entre a interface, os modelos e as regras de aplicação.
- **SQL**: esquema, dados iniciais e scripts de migração.

Ficheiros principais:

- `main.py`: ponto de entrada da aplicação.
- `View/app.py`: aplicação, autenticação, navegação e painel principal.
- `Model/auth.py`: autenticação e gestão da palavra-passe.
- `Model/alunos_turmas.py`: alunos e turmas.
- `Model/provas.py`: provas.
- `Model/competition_records.py`: inscrições, dorsais, chegadas, classificações, escalões e apuramentos.
- `Controllers/csv_tools_controller.py`: importação e exportação CSV.
- `Controllers/qr_reader_controller.py`: leitura de códigos QR.

## 3. Requisitos

### 3.1 Software

- Windows 10 ou posterior.
- Python 3.12 recomendado.
- MySQL 8.0 ou MariaDB 10.2 ou posterior.
- Câmara opcional para leitura de QR codes.
- Ficheiros da aplicação disponíveis localmente.

### 3.2 Dependências Python

O ficheiro `requirements.txt` contém:

```text
flet==1.1.2
flet-video==1.1.2
mysql-connector-python==26.10.0
Pillow==13.0.0
opencv-python==4.12.0.88
```

## 4. Instalação

### 4.1 Criar o ambiente virtual

Numa janela PowerShell aberta na pasta do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se a política do PowerShell impedir a ativação do ambiente virtual, utilize:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Os comandos seguintes podem usar diretamente o executável do ambiente virtual.

### 4.2 Criar a base de dados

Para uma instalação nova, execute por esta ordem:

```text
SQL/cortamatov0.5.sql
SQL/seedv0.5.sql
```

Exemplo no cliente MySQL:

```sql
SOURCE C:/Users/AEPBS/Downloads/cortamato-main/SQL/cortamatov0.5.sql;
SOURCE C:/Users/AEPBS/Downloads/cortamato-main/SQL/seedv0.5.sql;
```

O script `cortamatov0.5.sql` elimina a base de dados `cortamato` antes de a recriar. Não o execute numa instalação que contenha dados válidos.

O script `seedv0.5.sql` adiciona utilizadores, perfis, turmas, alunos, provas, escalões e dados de demonstração. As contas são criadas com a palavra-passe provisória `x`.

### 4.3 Configurar a ligação MySQL

Configure as variáveis de ambiente antes de iniciar a aplicação:

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "palavra-passe"
$env:MYSQL_DATABASE = "cortamato"
```

Os valores por defeito são:

| Variável | Valor por defeito |
|---|---|
| `MYSQL_HOST` | `localhost` |
| `MYSQL_PORT` | `3306` |
| `MYSQL_USER` | `root` |
| `MYSQL_PASSWORD` | vazio |
| `MYSQL_DATABASE` | `cortamato` |

### 4.4 Iniciar a aplicação

```powershell
.\.venv\Scripts\python.exe main.py
```

Também é possível abrir `main.py` no Visual Studio Code e executar o ficheiro com o ambiente `.venv`.

## 5. Modelo de dados

### 5.1 Identidade e acessos

- `utilizador`
- `perfil`
- `permissao`
- `utilizador_perfil`
- `perfil_permissao`

O modelo inclui os perfis `admin`, `professor`, `diretor_turma` e `secretariado`. O script de dados inicia atribuições de exemplo.

O ficheiro `SQL/seedv0.5.sql` concede ao perfil `admin` todas as permissões existentes no script. O controlo de permissões no modelo SQL deve ser configurado por perfis, mas a aplicação atual autentica utilizadores ativos e não carrega nem aplica cada permissão por recurso em todas as operações da interface.

### 5.2 Estrutura escolar

- `turma`
- `aluno`
- `prova`

### 5.3 Inscrições e participação

- `inscricao`
- `dorsal`
- `chegada`
- `desistencia`
- `desclassificacao`
- `lista_partida`
- `lista_partida_inscricao`

### 5.4 Resultados

- `escalao`
- `classificacao`
- `regra_apuramento`
- `apurado`

As relações com eliminação em cascata garantem que a remoção de provas, inscrições ou alunos remove os dados dependentes, conforme definido nas chaves estrangeiras.

## 6. Migração de bases de dados existentes

### 6.1 Chegadas

Se uma base de dados v0.5 existente ainda tiver o campo `hora_chegada` e não tiver `tempo_chegada`, execute uma vez:

```sql
SOURCE C:/Users/AEPBS/Downloads/cortamato-main/SQL/migrate_chegada_tempo.sql;
```

O script altera `chegada` e cria a vista `v_competidor`. Os timestamps antigos não são convertidos automaticamente para tempos decorridos.

As chegadas antigas podem aparecer sem tempo até serem editadas na aplicação.

### 6.2 Apuramentos

Se as tabelas `regra_apuramento` e `apurado` ainda não existirem:

```sql
SOURCE C:/Users/AEPBS/Downloads/cortamato-main/SQL/migrate_apuramentos.sql;
```

Esta migração não apaga dados existentes.

## 7. Utilização da aplicação

### 7.1 Início de sessão

No arranque, a aplicação apresenta o formulário de autenticação.

1. Introduza um email existente em `utilizador`.
2. Introduza a palavra-passe.
3. A conta tem de estar ativa.

As contas novas criadas pelo seed continuam a aceitar `x` enquanto tiverem o marcador `x` em `password_hash`.

Para alterar uma palavra-passe provisória:

```powershell
.\.venv\Scripts\python.exe -m Model.auth
```

Indique o email e introduza a nova palavra-passe duas vezes. A palavra-passe deve ter entre 8 e 128 caracteres.

Na aplicação, o utilizador pode ainda alterar o nome e a fotografia de perfil, o email e a palavra-passe através do menu de perfil.

### 7.2 Dashboard

O Dashboard apresenta um resumo da atividade:

- número de utilizadores;
- próximo evento;
- próximas provas;
- contagens de alunos inscritos;
- fotografia e nome do utilizador autenticado.

### 7.3 Provas

Permite listar, adicionar, editar e eliminar provas.

Campos principais:

- ano letivo;
- concelho;
- escola;
- data;
- hora de início;
- hora de fim.

### 7.4 Alunos e turmas

Permite:

- pesquisar alunos por nome ou número de processo;
- filtrar alunos por turma;
- ordenar por nome;
- criar, editar e eliminar alunos;
- criar, editar e eliminar turmas.

A eliminação de vários registos exige seleção e confirmação.

### 7.5 Inscrições

A secção permite gerir inscrições por prova:

- aluno;
- estado;
- indicador de desporto adaptado;
- função de organização;
- data de inscrição.

Estados disponíveis:

- `nao_inscrito`;
- `inscrito`;
- `participante`;
- `organizacao`.

### 7.6 Dorsais

Permite atribuir e gerir dorsais.

Estados disponíveis:

- `atribuido`;
- `entregue`;
- `devolvido`.

Um dorsal fica associado a uma inscrição. O número deve ser positivo e não pode estar repetido dentro da mesma prova.

### 7.7 Chegadas

Permite:

- registar um tempo de chegada;
- indicar o método `qrcode` ou `manual`;
- corrigir registos;
- selecionar a chegada corrigida.

Formato do tempo:

```text
MM:SS.mmm
```

Exemplos válidos:

```text
01:02.345
72:00.000
```

### 7.8 Classificações

Permite:

- associar uma inscrição a uma prova;
- selecionar um escalão ou classificação geral;
- indicar a posição.

### 7.9 Escalões e apuramentos

Permite definir escalões por:

- prova;
- designação;
- sexo;
- intervalo de anos de nascimento;
- indicador de desporto adaptado.

Permite definir regras que ligam uma prova de origem a uma prova de destino e indicam quantos atletas por escalão serão apurados.

Pode-se gerar os apuramentos para uma prova de destino e atualizar o estado de cada apurado:

- `apurado`;
- `confirmado`;
- `desistiu`.

## 8. Importação e exportação CSV

### 8.1 Importar turmas

Cabeçalhos esperados:

```csv
ano_escolar;letra
```

Também são aceites virgulas ou tabulações quando o Python deteta corretamente o delimitador.

### 8.2 Importar alunos

Cabeçalhos esperados:

```csv
numeroprocesso,nome,datanasc,sexo,ano_escolar,letra
```

Regras:

- datas no formato `AAAA-MM-DD`;
- sexo `M` ou `F`;
- ano escolar entre 1 e 12;
- o número de processo deve ser positivo;
- a turma referida deve existir;
- linhas duplicadas são ignoradas;
- linhas inválidas são apresentadas no resumo.

Para dados novos, importe primeiro as turmas e depois os alunos.

### 8.3 Exportar dados

Na secção **Importar e exportar**:

1. escolha a pasta de destino;
2. selecione `Alunos` ou `Turmas`;
3. clique em **Exportar CSV**.

Os ficheiros são guardados em UTF-8 com BOM e utilizam ponto e vírgula como delimitador.

### 8.4 Resumo da importação

Cada operação indica:

- número de registos importados;
- número de duplicados ignorados;
- número de linhas com erro;
- descrição das primeiras linhas inválidas;
- interrupção por falha de ligação à base de dados.

## 9. Leitor QR code

Além da secção integrada na aplicação principal, o leitor móvel está também na pasta autónoma `cortamato-web`, ao lado de `cortamato-main`. Essa pasta pode ser movida, copiada ou publicada num serviço de alojamento estático sem levar o resto do projeto. Não requer Python, API nem base de dados; a imagem QR é descodificada localmente no dispositivo.

Mantenha a estrutura de ficheiros dentro de `cortamato-web/`, incluindo `qr-mobile.html`, `manifest.webmanifest`, `service-worker.js`, `icon.svg` e `vendor/`. A aplicação não necessita de comandos ou serviços no servidor depois de publicada. A câmara ao vivo requer HTTPS; a seleção de imagem é descodificada no dispositivo e funciona sem enviar o ficheiro para o host. Em desenvolvimento, `python qr_app.py --web` usa essa pasta automaticamente quando existe; `QR_WEB_DIRECTORY` pode indicar outra localização.

### 9.1 Ler uma imagem

Na secção **Leitor QR code**:

1. clique em **Selecionar imagem**;
2. escolha uma imagem;
3. aguarde a descodificação;
4. se o conteúdo for HTTP ou HTTPS, será aberto no navegador.

Domínios sem protocolo são tratados como HTTPS.

### 9.2 Usar a câmara

1. clique em **Usar câmara**;
2. aproxime o QR code da lente;
3. prima `Q` ou `Esc` para fechar a janela da câmara.

A câmara deve estar ligada e disponível ao sistema operativo.

## 10. Modo de demonstração

A aplicação pode abrir sem ligação MySQL através do modo de demonstração:

1. na página de autenticação, selecione as letras `T`, `T`, `E`, `S` do texto CORTA/MATO/ESCOLAR;
2. as letras ficam vermelhas;
3. todas as secções ficam disponíveis com dados fictícios.

Neste modo, operações de criação, edição e eliminação são bloqueadas.

O modo de demonstração é adequado a apresentação e validação visual, não substitui testes reais da base de dados.

## 11. Segurança

### 11.1 Contas

- apenas utilizadores ativos podem autenticar;
- a palavra-passe provisória `x` é aceite apenas para contas que ainda usam esse marcador;
- palavras-passe novas são guardadas com PBKDF2-HMAC-SHA256;
- o cálculo usa 600 000 iterações e um salt aleatório;
- o email e o nome são validados antes da alteração.

### 11.2 Recomendações

- substituir todas as palavras-passe provisórias;
- usar uma palavra-passe MySQL dedicada à aplicação;
- não publicar os valores das variáveis de ambiente;
- restringir o utilizador MySQL às operações necessárias;
- executar cópias de segurança antes de eliminar dados;
- não executar `cortamatov0.5.sql` numa base de dados com dados.

## 12. Testes

### 12.1 Testes unitários

Execute:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes verificam:

- importação e duplicação de turmas;
- exportação e reimportação de alunos;
- datas inválidas e turmas desconhecidas;
- regra de origem/destino dos apuramentos;
- validação de URLs de QR codes;
- leitura de imagens QR;
- estrutura dos componentes Flet.

### 12.2 Compilação

Execute:

```powershell
.\.venv\Scripts\python.exe -m compileall -q .
```

Este comando verifica a sintaxe de todos os ficheiros Python.

### 12.3 Plano de testes funcional

| Caso | Procedimento | Resultado esperado |
|---|---|---|
| Login válido | Iniciar sessão com conta ativa | Abre o painel |
| Login inválido | Usar senha ou email incorreto | Mostra erro sem abrir o painel |
| Conta desativada | Autenticar conta com `ativo = FALSE` | Login recusado |
| Criar turma | Inserir ano e letra válidos | Turma criada |
| Duplicar turma | Repetir ano e letra existentes | Registo recusado/duplicado |
| Importar turmas CSV | Selecionar CSV válido | Resumo indica importados |
| Importar alunos CSV | Importar depois das turmas | Alunos criados |
| Linha inválida CSV | Usar data ou turma inválida | Linha indicada no resumo |
| Criar inscrição | Associar aluno e prova | Inscrição criada |
| Atribuir dorsal | Associar dorsal a inscrição | Dorsal atribuído |
| Dorsal repetido | Reutilizar número na prova | Operação recusada |
| Chegada manual | Introduzir `MM:SS.mmm` | Tempo guardado |
| Chegada QR | Ler ou introduzir QR válido | Participante associado |
| Corrigir chegada | Selecionar chegada anterior | Correção associada |
| Gerar apuramentos | Selecionar prova destino com regras | Apurados gerados |
| Exportar CSV | Escolher pasta e tipo | Ficheiro criado |
| Ler QR por imagem | Selecionar imagem válida | Conteúdo decodificado |
| Ler QR por câmara | Usar câmara disponível | Conteúdo decodificado ou cancelado |
| Modo demonstração | Usar sequência do ecrã de login | Dados fictícios sem escrita |

## 13. Registo de erros

A aplicação utiliza o módulo `logging` do Python.

Ocorrências comuns:

- `Unable to connect to MySQL`: ligação ou credenciais incorretas.
- `Unable to load...`: consulta inválida ou tabela inexistente.
- `Não foi possível ler a imagem...`: ficheiro não disponível ou imagem inválida.
- `Não foi possível aceder à câmara`: dispositivo ocupado ou sem permissões.
- `Faltam colunas obrigatórias`: CSV não corresponde ao formato esperado.

Antes de reportar um erro, registe:

1. versão do sistema operativo;
2. versão do Python;
3. versão do MySQL ou MariaDB;
4. mensagem apresentada;
5. passos executados;
6. ficheiro ou tabela envolvida.

## 14. Copias de segurança e restauro

### 14.1 Copia

Exemplo para MySQL:

```powershell
mysqldump -u root -p cortamato > backup-cortamato.sql
```

### 14.2 Restauro

```sql
CREATE DATABASE cortamato
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE cortamato;
SOURCE C:/caminho/backup-cortamato.sql;
```

Não execute o restauro sobre dados que devam ser preservados sem confirmar o destino.

## 15. Atualização do sistema

Antes de atualizar:

1. fazer cópia de segurança;
2. fechar a aplicação;
3. preservar o ficheiro `.env` ou as variáveis de ambiente;
4. atualizar o código;
5. atualizar as dependências;
6. executar as migrações necessárias;
7. executar os testes;
8. iniciar a aplicação.

Atualização das dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 16. Limitações atuais

O código implementado cobre autenticação, provas, turmas, alunos, inscrições, dorsais, chegadas, classificações, escalões, apuramentos, leitura QR, importação/exportação de alunos e turmas e modo de demonstração.

Algumas funções referidas no enunciado ainda dependem de desenvolvimento ou configuração externa:

- gestão completa de contas e permissões por interface;
- exportação de todos os tipos de relatórios descritos no projeto;
- envio de e-mail a Diretores de Turma;
- geração de diplomas com logótipos;
- estatísticas históricas comparativas;
- automatização integral da leitura de QR para todas as operações.

## 17. Ficheiros de referência

- `README.md`: instruções rápidas.
- `docs/analiseRequisitosv0.1.txt`: análise de requisitos.
- `docs/modeloERv0.2.png`: diagrama Entidade-Relação.
- `docs/modeloRelacionalv0.1.png`: modelo relacional.
- `docs/matrizPerfisPermissoesv1.0.xlsx`: perfis e permissões.
- `SQL/cortamatov0.5.sql`: instalação nova.
- `SQL/seedv0.5.sql`: dados iniciais.
- `SQL/migrate_chegada_tempo.sql`: migração das chegadas.
- `SQL/migrate_apuramentos.sql`: migração dos apuramentos.
- `tests/`: testes automatizados.
