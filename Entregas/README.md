# 📦 Entregas — Sec_Projects

Esta pasta centraliza as entregas dos projetos do repositório.

Ela deve ser usada para versionar as entregas de cada aluno ou equipe, mantendo um registro uniforme e fácil de avaliar.

## Estrutura de pastas

Use a seguinte estrutura básica:

- Projetos individuais:
  - `Entregas/<NomeDoAluno>/<NomeDoProjeto>/README.md`
- Projetos em grupo:
  - `Entregas/<NomeDaEquipe>/<NomeDoProjeto>/README.md`

### Exemplo

- `Entregas/Individual/Murilo_Miacci/Hash_ID/README.md`
- `Entregas/Team/InsperTeam/Hash_Cracker/README.md`

> Use underscores ou hífens em vez de espaços no nome da pasta.

## Como devem ser as entregas

Todas as entregas devem incluir um `README.md` padronizado com informações claras e objetivas. O arquivo deve documentar o que foi entregue, como validar a solução e quais artefatos estão presentes.

Cada entrega deve conter pelo menos:

- Identificação do projeto e do tipo (Individual / Team)
- Nome do aluno ou equipe
- Lista de arquivos entregues
- Instruções de validação
- Observações sobre o que foi implementado e o que ficou pendente
- Link para demo ou gravação, quando aplicável

## Template de entrega individual

```markdown
# Entrega Individual — <Nome do Projeto>

## Aluno

- Nome: <Seu nome completo>
- Curso / Semestre: <opcional>

## Projeto

- Frente: <Red Team / Blue Team / Purple Team>
- Modo: Individual
- Nível: <N1 / N2 / N3 / N4 / N5>
- Link do projeto: <caminho relativo ou URL>

## Resumo da entrega

Descreva em 2–3 frases o que foi implementado e o que está funcionando.

## O que foi entregue

- [ ] Funcionalidade obrigatória completada
- [ ] MVP atendido
- [ ] Extras implementados

## Como validar

1. Acesse a pasta do projeto original.
2. Execute os comandos descritos em `README.md`.
3. Verifique os resultados esperados.

## Arquivos entregues

- `README.md`
- `DEMO.md` (se aplicável)
- `src/` ou código fonte
- `tests/` ou casos de teste
- outros artefatos relevantes

## Observações

- Pontos de atenção
- Dependências especiais
- O que ficou pendente

## Link para demo

- <URL para gravação / screenshots / ascinema>
```

## Template de entrega em equipe

```markdown
# Entrega em Grupo — <Nome do Projeto>

## Equipe

- Nome da equipe: <Nome da equipe>
- Membros:
  - <Nome 1> — <responsabilidade>
  - <Nome 2> — <responsabilidade>
  - <Nome 3> — <responsabilidade>

## Projeto

- Frente: <Red Team / Blue Team / Purple Team>
- Modo: Team
- Nível: <N4 / N5>
- Link do projeto: <caminho relativo ou URL>

## Resumo da entrega

Descreva em 2–3 frases o resultado entregue pela equipe.

## O que foi entregue

- [ ] Funcionalidade obrigatória completada
- [ ] MVP atendido
- [ ] Integração da equipe documentada
- [ ] Testes e validação realizados

## Como validar

1. Acesse a pasta do projeto original.
2. Execute os comandos descritos em `README.md`.
3. Confirme cada resultado listado na seção anterior.

## Divisão de trabalho

- <Nome 1>: <tarefas>
- <Nome 2>: <tarefas>
- <Nome 3>: <tarefas>

## Arquivos entregues

- `README.md`
- `DEMO.md`
- `src/`
- `tests/`
- `relatório.pdf` ou `slides/` (se aplicável)

## Observações

- Pontos de atenção
- O que foi feito por cada membro
- O que ficou pendente

## Link para demo

- <URL para gravação / screenshots / ascinema>
```

## Instruções de Pull Request

1. Crie uma branch para a entrega:
   - `git switch -c nome-da-branch`
2. Adicione a pasta de entrega em `Entregas/`.
3. Inclua o `README.md` de entrega e os arquivos de suporte.
4. Faça commit com mensagem clara:
   - `docs: entrega de <NomeDoProjeto> - <Aluno ou Equipe>`
5. Faça push e abra um PR para `main`.
6. No PR, descreva:
   - O que foi entregue
   - Como validar
   - Qual projeto foi atendido
   - Se há pendências ou detalhes específicos

> O PR deve ser direcionado ao avaliador responsável pelo repositório, com a entrega pronta para revisão.

## Links úteis

- [Guia de Workflow](../docs/WORKFLOW.md)
- [Mapa Curricular](../docs/CURRICULUM.md)
- [Guia de Demo](../docs/DEMO_GUIDE.md)
- [Padrões de README](../CONTRIBUTING.md#-padr%C3%B5es-de-readme)
