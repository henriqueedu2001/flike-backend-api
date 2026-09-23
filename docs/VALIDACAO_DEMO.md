# Verificação da demonstração — 23/09/2026

Ambiente local isolado: MySQL 8.4.8, Python 3.13, Node 24.13 e frontend Next.js 16.3.6. As alterações estão nas branches `codex/demo-ready` dos repositórios de código; a tese não foi modificada.

| Verificação | Resultado |
|---|---|
| API + banco MySQL real | 43 testes passaram |
| Regras de payload, parser, QR 3-L e validade no frontend | 4 testes passaram |
| Navegador Chromium desktop 1366×900 e celular 390×844 | Fluxo completo passou nos dois viewports |
| Sessão inválida, login incorreto e recuperação após falha de rede | Teste de navegador passou |
| Build de produção e lint | Passaram |
| `npm audit` após atualização compatível | Nenhuma vulnerabilidade reportada |

O roteiro de navegador cadastra duas contas, cria instituição/edifício/sala/tranca, solicita acesso, aprova, recupera o QR, recarrega, rejeita outro pedido, consulta o histórico e sai/entra novamente. O QR exibido é decodificado por ZXing e comparado aos 48 bytes reais da API. A apresentação de uma chave expirada é exercitada avançando somente o relógio do navegador.

Os testes de API cobrem autorização entre contas, exclusões com vínculos, datas UTC, vetor CMAC da tese, ausência de segredos nas respostas, decisões simultâneas, rollback após falha e migração que preserva registros legados. Os testes usam banco separado; o seed da demonstração prepara apenas dados fictícios e é repetível.

Imagens dos testes ficam em `artifacts/e2e/`, ignoradas pelo Git. Para reproduzir: `./scripts/demo.sh test` e `./scripts/demo.sh e2e`; no frontend, `npm run lint` e `npm run test:unit`. O roteiro e a inicialização estão no README do backend. Os dados de login local ficam em `.demo/ACESSO.md`.

Escopo mantido: uma tranca por sala na demonstração; sem RF-04, revogação imediata, app móvel ou alegações de entrada/ocupação. Esta verificação cobre o site, sua API e o conteúdo do QR; não é teste com participantes nem certificação do dispositivo físico.
