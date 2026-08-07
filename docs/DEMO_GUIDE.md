# 🎬 Guia de Demo e Apresentação — Sec_Projects

> Documento transversal que define como cada projeto deve ser demonstrado e apresentado, uniformizando a entrega final.

---

## 1. Objetivo da Demo

A demo é a **prova prática** de que o projeto foi concluído. Ela deve mostrar:

- Que a ferramenta **funciona** de verdade;
- Que o autor **entende** o que construiu;
- Que as decisões técnicas são **justificáveis**;
- Que o aprendizado pode ser **compartilhado** com outros membros.

---

## 2. Formatos de Demo

A demo pode ser apresentada em **dois formatos complementares**:

### 2.1 Demo ao vivo (presencial ou remota)

Execução em tempo real, com o autor explicando o fluxo enquanto interage com a ferramenta. É o formato padrão para apresentações à Insper Sec.

### 2.2 Demo gravada (assíncrona)

Uma gravação da execução, útil para:

- Revisão posterior;
- Documentação do projeto (`DEMO.md`);
- Membros que não puderam comparecer à apresentação.

**Formatos recomendados para gravação:**

| Formato       | Descrição                                             | Uso ideal                                       |
| ------------- | ----------------------------------------------------- | ----------------------------------------------- |
| **asciinema** | Gravação de terminal em texto (SVG/player interativo) | Demos de CLI, saída de terminal, comandos       |
| **GIF**       | Gravação curta de tela em loop                        | Demonstração visual de interface, TUI, gráficos |
| **Vídeo**     | Gravação de tela com áudio (MP4/WebM)                 | Demos completas com narração                    |

> **Recomendação:** para projetos de linha de comando (CLI), prefira **asciinema** ou **GIFs** — são leves, fáceis de incorporar no README e mostram exatamente o que acontece no terminal. Exemplos de ferramentas: [`asciinema`](https://asciinema.org), [`agg`](https://github.com/asciinema/agg) (para gerar GIF a partir de asciinema) e [`peek`](https://github.com/phw/peek) (para gravar GIFs de tela).

---

## 3. Estrutura Recomendada da Demo

Uma demo deve durar **5–10 minutos** e seguir esta estrutura:

### 3.1 Contexto (1 min)

- Qual é o problema que o projeto resolve?
- Por que isso importa em segurança?

### 3.2 O que foi construído (1 min)

- Visão geral da ferramenta/script.
- Stack utilizada.
- Arquitetura principal (fluxo de dados).

### 3.3 Execução ao vivo (3–5 min)

- Execute a ferramenta com um caso real.
- Mostre a saída esperada.
- Explique **o que está acontecendo** em cada etapa.

### 3.4 Decisões técnicas (1–2 min)

- Explique 1–2 decisões importantes:
  - Por que escolheu essa abordagem?
  - Que trade-offs enfrentou?
  - O que você faria diferente?

### 3.5 Validação e testes (1 min)

- Mostre que os testes passam (`just test`, `just lint`).
- Mostre a validação da seção `Validation` do README.

### 3.6 Próximos passos (30s)

- O que você aprendeu?
- Para onde o projeto aponta (Next Step)?

---

## 4. Critérios de Avaliação da Demo

| Critério           | O que é avaliado                                   |
| ------------------ | -------------------------------------------------- |
| **Funcionalidade** | A ferramenta executa e produz o resultado esperado |
| **Compreensão**    | O autor explica o que está acontecendo e por quê   |
| **Validação**      | Testes e validação documentados foram executados   |
| **Comunicação**    | A apresentação é clara, objetiva e técnica         |
| **Segurança**      | A demo foi executada em ambiente autorizado        |

---

## 5. Checklist de Apresentação

Antes de apresentar, verifique:

- [ ] Ambiente preparado (dependências instaladas, tooling funcionando)
- [ ] Alvo autorizado (próprio ambiente, CTF, lab local)
- [ ] Comandos testados previamente (sem surpresas ao vivo)
- [ ] Saída esperada conhecida
- [ ] 1–2 decisões técnicas para explicar
- [ ] Testes passando (`just test`, `just lint`)
- [ ] Demo documentada (se aplicável, `DEMO.md` atualizado)

---

## 6. Dicas

- **Não leia o código linha por linha** — mostre o fluxo e explique o raciocínio.
- **Use casos reais** — demonstre com dados/hashes/alvos que façam sentido.
- **Mostre o erro também** — se algo falhar, explique por quê (é tão valioso quanto o sucesso).
- **Mantenha o ritmo** — 10 minutos no máximo, foque no essencial.
- **Respeite o ambiente** — nunca demonstre em sistemas sem autorização.

---

## 7. Projetos Team — Demo em Grupo

Para projetos Team, a demo deve:

- Mostrar a **integração** dos submódulos (não só o trabalho individual).
- Dar visibilidade à contribuição de **cada membro**.
- Explicar como os workstreams foram integrados.
- Cobrir os **milestones** alcançados.

### Divisão da apresentação (sugestão)

| Membro | Papel na demo                                |
| ------ | -------------------------------------------- |
| M1     | Contexto + visão geral + arquitetura         |
| M2     | Execução ao vivo + validação                 |
| M3     | Decisões técnicas + testes + próximos passos |

---

## 8. Referências

- [Guia de workflow](./WORKFLOW.md) — como executar e validar projetos
- [Mapa curricular](./CURRICULUM.md) — onde cada projeto se encaixa
