# adrcheck documentation

Start with the first two if adrcheck is new to you. The rest are reference.

| Page | Read it when |
|---|---|
| [Getting started](getting-started.md) | you want a first report in ten minutes and to know what each line of it means |
| [What the verdicts mean](verdicts.md) | a report says CONFLICT, UNCLEAR or ADR-OVERTAKEN and you want the exact definition, or `lint` printed a code |
| [The flow](workflow.md) | you want the picture: what happens inside a run, and what a team does around it |
| [Use cases](use-cases.md) | you joined a team with ADRs, or you have ADRs and want them enforced, or you want the check in every pull request |
| [Writing ADRs that compile](writing-adrs.md) | you are writing or amending a record and want the judge to be able to hold code to it |
| [Providers](providers.md) | choosing a model, running on OpenRouter or Ollama, bounding the bill |
| [Design](design.md) | how adrcheck is built and which design rules it follows or bends |

The decisions behind adrcheck are its own ADRs under [adr/](adr/), and adrcheck checks itself against
them. Measurements that back a claim in these pages are under [spikes/](spikes/), dated.
