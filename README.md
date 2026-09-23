# FLIKE — demonstração integrada

Esta versão conecta a aplicação Next.js, API FastAPI e MySQL. O roteiro cobre cadastro, login, gestão da estrutura institucional, solicitação, aprovação/rejeição, consulta persistente do QR e histórico de autorizações emitidas.

## Preparação

Requisitos: Python **3.12+**, Node.js **24** (validado com 24.13), npm e Docker com Compose. Mantenha os repositórios `flike-backend-api` e `flike-frontend-webpage` como pastas irmãs. Se necessário, defina `FLIKE_FRONTEND_DIR` para outro caminho. As ferramentas opcionais de firmware usam `flike-firmware` como pasta irmã.

Na raiz do backend:

```bash
./scripts/demo.sh setup
./scripts/demo.sh build-web
```

Na primeira preparação, dependências e a imagem MySQL precisam de internet. A execução posterior usa os serviços locais. `.env.demo` é criado com credenciais aleatórias, permissão 0600 e exclusão do Git; o `.env` existente não é substituído. O banco da demonstração fica na porta **55470**, com volume próprio. O banco de testes fica na porta **55471**, em armazenamento temporário. Os containers existentes `mysql-flike` e seus dados permanecem separados.

`setup` pode ser repetido. Um schema antigo/incompleto é rejeitado com instrução clara; a migração SQL disponível em `migrations/` nunca é aplicada automaticamente. Para atualizar um banco antigo, faça backup e examine a migração separadamente.

## Iniciar

Terminal 1:

```bash
./scripts/demo.sh api
```

Terminal 2:

```bash
./scripts/demo.sh seed
./scripts/demo.sh web
```

Abra **http://127.0.0.1:3000**. A API fica em **http://127.0.0.1:18000**. O seed é idempotente e prepara duas instituições, cada uma com edifício, sala e uma tranca. Ele não gera pedidos ou aprovações automaticamente.

As contas fictícias são `responsavel@example.com`, `visitante@example.com` e `outro@example.com`. A senha local aparece em `.demo/ACESSO.md` ou com:

```bash
./scripts/demo.sh credentials
```

Para encerrar API e site, use Ctrl+C em seus terminais. `./scripts/demo.sh stop` para os bancos da demonstração/testes e **preserva o volume da demonstração**. Não há comando de reset destrutivo implícito.

## Roteiro para a apresentação

1. Abra dois perfis/janelas privadas do navegador: responsável e solicitante. Também é possível cadastrar uma conta nova na tela **Criar Conta**.
2. Com `responsavel@example.com`, entre em **Estrutura institucional** e mostre instituição → edifício → sala → tranca. Cadastros, edições e exclusões de recursos vazios são permitidos; exclusões com vínculos são recusadas.
3. Com o visitante, abra **Solicitar acesso**, escolha **FLIKE — Demonstração**, seu edifício e **Sala de apoio**, e envie. O painel mostra **Pendente**.
4. Com o responsável, abra **Solicitações recebidas** e aprove o pedido. A validade padrão é de 24 horas; a tela também permite informar minutos.
5. Atualize o painel do visitante: o pedido fica **Aprovada** e a chave pode ser aberta em **Ver QR Code**. Recarregue a página ou saia/entre novamente para demonstrar a recuperação da mesma chave.
6. Envie outro pedido e rejeite-o como responsável. O visitante verá **Rejeitada**, sem uma nova chave.
7. Abra **Autorizações emitidas** e o histórico do solicitante. Os registros representam emissão, destino e validade — não passagem pela porta.
8. Entre como `outro@example.com`: essa conta administra apenas a instituição independente. A API também bloqueia tentativas de consultar/modificar recursos protegidos de terceiros.

A demo utiliza **uma tranca por sala**: seleção explícita entre múltiplas trancas (RF-04) continua fora do escopo aprovado. Chaves são reutilizáveis até expirar, não consumidas por uma flag de uso. Sem aplicativo móvel, recuperação de senha, revogação imediata, gestão visual de segredo ou monitoramento de ocupação.

## Verificação reproduzível

```bash
./scripts/demo.sh test
./scripts/demo.sh e2e
```

O primeiro comando usa MySQL real isolado para verificar autenticação, CRUD contextual, sigilo, decisões concorrentes, rollback, validade/CMAC e migração de dados legados em tabelas temporárias de teste.

O segundo instala o Chromium de testes, compila o frontend em **`.next-e2e`**, inicia API **18001** e site **3001** contra `flike_test`, executa o fluxo em viewports desktop/celular e encerra apenas os processos que criou. O build da apresentação em `.next` é preservado. As imagens ficam em `artifacts/e2e/`; logs em `.demo/e2e-*.log`. O QR efetivamente exibido pelo navegador é decodificado por ZXing e comparado byte a byte ao payload da API.

Os testes não certificam usabilidade com participantes nem leitura óptica pela ESP32-CAM.

## Ensaio físico

O protocolo permanece: 4 inteiros de 64 bits big-endian (usuário, tranca, emissão e expiração), seguidos de AES-CMAC de 16 bytes: **48 bytes**, QR **versão 3-L**. A janela é `emissão <= agora < expiração`.

A demonstração não exige ligação USB/serial entre a placa e o computador: o canal entre site e dispositivo é apenas o QR Code. Uma placa já programada deve manter seu firmware e seus parâmetros; o ID e o segredo da tranca no backend precisam corresponder aos já provisionados nela. O seed gera trancas novas, portanto não pressupõe essa correspondência com a placa existente.

No repositório do firmware há testes host, build PlatformIO e instruções de bancada. **Somente para preparar um novo firmware**, pode-se exportar o segredo de uma tranca da demonstração diretamente do banco para o arquivo local ignorado pelo Git:

```bash
./scripts/demo.sh provision ID_DA_TRANCA
```

O comando não mostra o segredo, não substitui uma configuração existente e mantém o relé desabilitado. O cabeçalho local contém material secreto e deve permanecer fora do Git. Configuração e operação do dispositivo são independentes do site. O mecanismo serial do firmware preparado é uma ferramenta opcional de bancada, não um requisito do site nem do roteiro da apresentação.

A validação entregue do site cobre os fluxos web e os bytes do QR. A operação física da placa permanece independente desse trabalho.
