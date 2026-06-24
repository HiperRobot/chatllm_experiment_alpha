# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
_State clearly what you are trying to achieve and the architectural constraints, avoiding implementation specifics of HOW to do it. Focus on WHAT and WHY._
O usuario deve poder se cadastrar, logar e deslogar do sistema para ser diferenciado de outros usuarios no salvamento de suas mensagens / conversas por exemplo (esse salvamento das conversas/mensagens nao deve ocorrer agora e sim só numa futura issue/task). Qualquer usuario deve poder usar essa funcionalidade ao clicar em um botão no topo da tela.

## Steps
- [ ] _Decompose the problem into actionable logical steps._
- [ ] _Each step should represent a verifiable piece of work._
- [ ] Tem que ter um banco de dados com os cadastros, rotas de cadastro, login, logout, validação etc.
- [ ] Criar modelo User no SQLAlchemy
- [ ] Criar rota POST /api/auth/register (cadastro com hash de senha)
- [ ] Criar rota POST /api/auth/login (valida credenciais e cria sessão)
- [ ] Criar rota POST /api/auth/logout (imterrompe a sessão)
- [ ] Criar rota GET /api/auth/me (retorna usuário da sessão atual)
- [ ] Tambem altere o front end para dar a opção (apenas se o usuario clicar no botao no topo da tela) de se cadastrar ou logar no sistema para salvar as suas conversas e mensagens.
- [ ] Criar componente de formulario de login e cadastro no frontend
- [ ]  Criar botão de login/logout no topo da tela
- [ ] Primeiro precisa existir a base/logica no backend para depois fazermos os componentes que usem isso no frontend.
- [ ] Adicionar disclaimer conforme estado de autenticação
- [ ] Escrever testes automatizados para todas as rotas

## Success Looks Like
- [ ] _Define rigorous, observable criteria for success. E.g., The endpoint returns 200 OK with the user object, NOT Code compiles_
Quando o usuario faz o login com dados correr deve retornar 200 OK com o objeto do usuario.
Se ele fornecer um usuario que existe mas uma senha errada deve retornar senha errada. Já se fornecer um usuario que não exista deve enviar usuario não cadastrado e já jogar o usuario pra tela de cadastro desse usuario não existente.
Na tela de cadastro o usuario deve botar a senha duas vezes e elas precisam bater. Na tela de login usuario e senha precisam bater com o q esta no nosso banco.
Para saber que o logout funcionou tem q retornar 200 Ok no endpoint dele e ficar sem nenhum usuario selecionado no campo de usuario atual, nesse caso seria bom colocar um disclaimer de que sem usuario logado as conversas e mensagens não serão salvas.
Faça testes automatizados que garantem o funcionamento do que eu descrevi.

## Notes
- [ ] _Any specific edge cases, libraries to consider, or potential pitfalls._
- [ ] Armazenar as senhas com Hash
- [ ] Armazena a sessão no próprio SQLite
- [ ] O usuario pode acessar o chat sem estar logado, mas tera um disclaimer de que as msgs nao serão salvas até ele se logar e quando ele estiver logado um disclaimer de que as msgs estão sendo salvas na conta de: "nome do usuario"

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
