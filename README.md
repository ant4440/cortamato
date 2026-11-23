# Cortamato

Aplicação de gestão de provas de atletismo escolar, com autenticação por email e palavra-passe e ligação à base de dados MySQL.

## Acesso (fase 1)

As contas de exemplo em `SQL/seedv0.4.sql` usam a palavra-passe provisória `x`. A autenticação aceita `x` apenas para contas cujo `password_hash` ainda contém esse marcador.

Configure a ligação MySQL através das variáveis `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` e `MYSQL_DATABASE`.

Para substituir o marcador e definir uma palavra-passe individual:

```powershell
python -m Model.auth
```

O comando pede o email e a nova palavra-passe sem a mostrar no terminal. As palavras-passe novas têm de ter entre 8 e 128 caracteres e são guardadas com PBKDF2-HMAC-SHA256.

## Executar

```powershell
python -m pip install -r requirements.txt
python main.py
```

A janela começa no formulário de autenticação e passa ao painel após um início de sessão válido.

Para abrir a demonstração sem uma ligação MySQL, clique no `T` de “CORTA”, no `T` de “MATO” e no `E` e `S` de “ESCOLAR”, em qualquer ordem. As letras ficam vermelhas ao serem selecionadas. Todas as secções ficam disponíveis para consulta com dados fictícios; as ações de criação, edição e eliminação ficam desativadas. O aviso “DADOS FICTÍCIOS” pisca no menu lateral.

## Atualização das chegadas

As chegadas são guardadas como tempos decorridos (`MM:SS.mmm`), não como data e hora. Numa base de dados v0.5 já existente, execute `SQL/migrate_chegada_tempo.sql` uma vez antes de atualizar a aplicação. O script preserva os valores antigos de `hora_chegada`, que não podem ser convertidos com segurança em tempos decorridos; nas provas ainda listadas pela aplicação, as chegadas antigas aparecem sem tempo até que este seja preenchido ao editar o registo.

## Alunos e turmas

A secção permite pesquisar alunos por nome ou número de processo, filtrar por turma, ordenar por nome (A–Z/Z–A) e adicionar, editar ou eliminar alunos e turmas. A eliminação exige seleção e confirmação; apagar alunos também apaga as respetivas inscrições e dados associados.
