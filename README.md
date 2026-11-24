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
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

No VS Code, abra `main.py` e use o botão **Run Python File**; a configuração do workspace seleciona o ambiente `.venv`. Também pode usar **Run and Debug** e escolher `Cortamato: executar main.py`.

A janela começa no formulário de autenticação e passa ao painel após um início de sessão válido.
As listagens de provas e respetivos registos incluem também provas passadas; o dashboard continua a destacar apenas as próximas provas.

Para abrir a demonstração sem uma ligação MySQL, clique no `T` de “CORTA”, no `T` de “MATO” e no `E` e `S` de “ESCOLAR”, em qualquer ordem. As letras ficam vermelhas ao serem selecionadas. Todas as secções ficam disponíveis para consulta com dados fictícios; as ações de criação, edição e eliminação ficam desativadas. O aviso “DADOS FICTÍCIOS” pisca no menu lateral.

## Atualização das chegadas

As chegadas são guardadas como tempos decorridos (`MM:SS.mmm`), não como data e hora. Numa base de dados v0.5 já existente, execute `SQL/migrate_chegada_tempo.sql` uma vez antes de atualizar a aplicação. O script preserva os valores antigos de `hora_chegada`, que não podem ser convertidos com segurança em tempos decorridos; nas provas ainda listadas pela aplicação, as chegadas antigas aparecem sem tempo até que este seja preenchido ao editar o registo.

## Atualização dos apuramentos

Numa base de dados existente que ainda não tenha as tabelas `regra_apuramento` e `apurado`, execute `SQL/migrate_apuramentos.sql`. Esta migração cria apenas as tabelas em falta e não apaga dados. Não execute `SQL/cortamatov0.5.sql` numa base de dados existente: esse script recria a base de dados.

## Alunos e turmas

A secção permite pesquisar alunos por nome ou número de processo, filtrar por turma, ordenar por nome (A–Z/Z–A) e adicionar, editar ou eliminar alunos e turmas. A eliminação exige seleção e confirmação; apagar alunos também apaga as respetivas inscrições e dados associados.

## Leitor QR code

A secção **Leitor QR code** permite selecionar uma imagem ou usar a câmara. Os endereços HTTP/HTTPS abrem no navegador predefinido; se o QR contiver um domínio sem protocolo, é usado HTTPS. Na janela da câmara, prima `Q` ou `Esc` para fechar o leitor.

## Importar e exportar

A secção **Importar e exportar** apresenta campos para escolher os ficheiros CSV de turmas e de alunos e botões para iniciar cada importação. Importe primeiro as turmas; os alunos usam os cabeçalhos exportados pela aplicação e datas no formato `AAAA-MM-DD`. Na exportação, escolha a pasta, o tipo de relatório e clique em **Exportar CSV**. Registos duplicados são ignorados e apresentados no resumo; linhas inválidas também são indicadas. As operações CSV requerem uma sessão autenticada e ligação à base de dados.

## Aplicação autónoma do leitor QR

A aplicação principal mantém a secção **Leitor QR code**. Também existe um ponto de entrada próprio:

```powershell
.\.venv\Scripts\python.exe qr_app.py
```

O leitor móvel está também disponível, em cópia autónoma, na pasta `cortamato-web` ao lado da pasta do projeto. Podes mover essa pasta ou publicar o seu conteúdo num serviço de alojamento estático sem levar o resto do projeto. Não precisa de servidor Python, API ou base de dados: a descodificação de imagens é feita localmente no navegador e a aplicação não envia a imagem para fora do dispositivo. Mantém a estrutura dos ficheiros (`qr-mobile.html`, `manifest.webmanifest`, `service-worker.js`, `icon.svg` e `vendor/`).

Abra o endereço HTTPS do host no telemóvel e, se desejar, use **Adicionar ao ecrã principal** para o instalar como aplicação. HTTPS é necessário para a câmara ao vivo; a seleção de imagem também funciona sem acesso à câmara. Para testar localmente, `qr_app.py --web` usa automaticamente `cortamato-web` se existir ao lado do projeto; a variável `QR_WEB_DIRECTORY` permite indicar outro caminho.

Para Netlify ligado a este repositório, o ficheiro `netlify.toml` seleciona `web/` como pasta publicada. Para publicação manual, envie o conteúdo completo de `cortamato-web/`; o `index.html` encaminha automaticamente para o leitor QR.

Também está preparada a publicação pelo GitHub Pages através de `.github/workflows/deploy-qr-pages.yml`. Ative **Settings → Pages → Build and deployment → GitHub Actions** no repositório e publique os ficheiros em `main`. O endereço será `https://ant4440.github.io/cortamato/`. O site Netlify atual está marcado como privado; para o tornar público, desative a proteção de acesso do site nas definições do Netlify ou utilize o URL do GitHub Pages.
