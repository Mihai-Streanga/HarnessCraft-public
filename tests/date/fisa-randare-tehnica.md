# Fișa dinaintea interviului — „prompter”

*Scor necalibrat, nivel provizoriu: calculate din reguli scrise, fără validare pe candidați reali. Arată ce se vede în git; interviul confirmă sau infirmă.*

## Nivel provizoriu: **prompter** (1 din 4)

Pentru configurator lipsește: instrucțiuni cu secțiuni, comenzi și interdicții.

## Scor pe principii: 2 din 16

**verificarea există și e folosită: 0 din 4**

- ✗ teste
- ✗ CI
- ✗ hooks git
- ✗ hooks de agent

**ce e de făcut e specificat dinainte: 2 din 4**

- ✓ secțiuni: 8 secțiuni în CLAUDE.md
- ✓ comenzi: `pytest -q`; `npm test`
- ✗ interdicții: 0 interdicții
- ✗ structură: 0 skills, 0 comenzi, 0 subagenți, 0 reguli scoped

**arhitectura e exprimată și ținută la zi: 0 din 4**

- ✗ cel puțin 3 căi citate: 2 căi citate
- ✗ cel mult 20% lipsă: 2 din 2 există
- ✗ trimit la arhitectură sau decizii
- ✗ spun cum e organizat proiectul

**responsabilitatea: 0 din 4**

- ✗ nicio cheie în cod acum: 1 în arbore
- ✗ nicio cheie în istoric: 2 găsiri
- ✗ licență recunoscută: lipsă
- ✗ urma AI în commit-uri: 0 commit-uri o declară

## Goluri — de acoperit la interviu

**metoda se schimbă după eșecuri.** Din git nu se vede: semnalul de cicatrice a ieșit la nivelul întâmplării.
> Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?

**manual sau agent, cu cost.** Din git nu se vede ce a ales omul să facă singur.
> Ce nu lăsați AI-ului să facă, deși ar putea? De ce?

## Ce nu se vede din fișa asta

- dacă testele sunt bune; calitatea codului; munca fără urme în git;
- un harness bogat arată un proiect pregătit pentru agent, nu că omul e bun: se poate și copia;
- licențele dependențelor; o cheie prinsă numai de forma generală (se spune lângă, nu scade).


=====

# Fișa dinaintea interviului — „configurator”

*Scor necalibrat, nivel provizoriu: calculate din reguli scrise, fără validare pe candidați reali. Arată ce se vede în git; interviul confirmă sau infirmă.*

## Nivel provizoriu: **configurator** (2 din 4)

Pentru constructor de sistem lipsește: structură: skills, comenzi, subagenți sau reguli scoped; teste care rulează automat: CI, sau un hook care rulează testele.

## Scor pe principii: 10 din 16

**verificarea există și e folosită: 1 din 4**

- ✓ teste: 1 fișiere de test
- ✗ CI
- ✗ hooks git
- ✗ hooks de agent

**ce e de făcut e specificat dinainte: 3 din 4**

- ✓ secțiuni: 8 secțiuni în CLAUDE.md
- ✓ comenzi: `pytest -q`; `npm test`
- ✓ interdicții: 5 interdicții
- ✗ structură: 0 skills, 0 comenzi, 0 subagenți, 0 reguli scoped

**arhitectura e exprimată și ținută la zi: 4 din 4**

- ✓ cel puțin 3 căi citate: 17 căi citate
- ✓ cel mult 20% lipsă: 17 din 17 există
- ✓ trimit la arhitectură sau decizii: `ARCHITECTURE.md`, `docs/adr/0001.md`
- ✓ spun cum e organizat proiectul: „Project Structure”; „Arhitectura”

**responsabilitatea: 2 din 4**

- ✓ nicio cheie în cod acum: 0 în arbore
- ✗ nicio cheie în istoric: 1 găsiri
- ✗ licență recunoscută: nerecunoscută
- ✓ urma AI în commit-uri: 1 commit-uri o declară

## Goluri — de acoperit la interviu

**metoda se schimbă după eșecuri.** Din git nu se vede: semnalul de cicatrice a ieșit la nivelul întâmplării.
> Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?

**manual sau agent, cu cost.** Din git nu se vede ce a ales omul să facă singur.
> Ce nu lăsați AI-ului să facă, deși ar putea? De ce?

## Ce nu se vede din fișa asta

- dacă testele sunt bune; calitatea codului; munca fără urme în git;
- un harness bogat arată un proiect pregătit pentru agent, nu că omul e bun: se poate și copia;
- licențele dependențelor; o cheie prinsă numai de forma generală (se spune lângă, nu scade).


=====

# Fișa dinaintea interviului — „constructor”

*Scor necalibrat, nivel provizoriu: calculate din reguli scrise, fără validare pe candidați reali. Arată ce se vede în git; interviul confirmă sau infirmă.*

## Nivel provizoriu: **constructor de sistem** (3 din 4)

Pentru metodolog (provizoriu) lipsește: instrucțiuni ținute la zi: cel puțin 3 căi citate, cel mult 20% lipsă.

## Scor pe principii: 13 din 16

**verificarea există și e folosită: 3 din 4**

- ✓ teste: 45 fișiere de test
- ✓ CI: .github/workflows/ci.yml
- ✓ hooks git: .githooks/pre-commit
- ✗ hooks de agent

**ce e de făcut e specificat dinainte: 4 din 4**

- ✓ secțiuni: 8 secțiuni în CLAUDE.md
- ✓ comenzi: `pytest -q`; `npm test`
- ✓ interdicții: 5 interdicții
- ✓ structură: 2 skills, 0 comenzi, 0 subagenți, 0 reguli scoped

**arhitectura e exprimată și ținută la zi: 2 din 4**

- ✓ cel puțin 3 căi citate: 17 căi citate
- ✗ cel mult 20% lipsă: 13 din 17 există; lipsă: `docs/vechi.md`, `src/x.py`, `a/b.md`
- ✗ trimit la arhitectură sau decizii
- ✓ spun cum e organizat proiectul: arbore de dosare

**responsabilitatea: 4 din 4**

- ✓ nicio cheie în cod acum: 0 în arbore
- ✓ nicio cheie în istoric: 0 găsiri
- ✓ licență recunoscută: MIT
- ✓ urma AI în commit-uri: 1 commit-uri o declară

## Goluri — de acoperit la interviu

**metoda se schimbă după eșecuri.** Din git nu se vede: semnalul de cicatrice a ieșit la nivelul întâmplării.
> Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?

**manual sau agent, cu cost.** Din git nu se vede ce a ales omul să facă singur.
> Ce nu lăsați AI-ului să facă, deși ar putea? De ce?

## Ce nu se vede din fișa asta

- dacă testele sunt bune; calitatea codului; munca fără urme în git;
- un harness bogat arată un proiect pregătit pentru agent, nu că omul e bun: se poate și copia;
- licențele dependențelor; o cheie prinsă numai de forma generală (se spune lângă, nu scade).


=====

# Fișa dinaintea interviului — „metodolog”

*Scor necalibrat, nivel provizoriu: calculate din reguli scrise, fără validare pe candidați reali. Arată ce se vede în git; interviul confirmă sau infirmă.*

## Nivel provizoriu: **metodolog (provizoriu)** (4 din 4)

## Scor pe principii: 14 din 16

**verificarea există și e folosită: 3 din 4**

- ✓ teste: 45 fișiere de test
- ✓ CI: .github/workflows/ci.yml
- ✗ hooks git
- ✓ hooks de agent: .claude/hooks/x.py

**ce e de făcut e specificat dinainte: 4 din 4**

- ✓ secțiuni: 8 secțiuni în CLAUDE.md
- ✓ comenzi: `pytest -q`; `npm test`
- ✓ interdicții: 5 interdicții
- ✓ structură: 1 skills, 0 comenzi, 0 subagenți, 0 reguli scoped

**arhitectura e exprimată și ținută la zi: 3 din 4**

- ✓ cel puțin 3 căi citate: 17 căi citate
- ✓ cel mult 20% lipsă: 16 din 17 există; lipsă: `docs/vechi.md`
- ✓ trimit la arhitectură sau decizii: `docs/DECISIONS.md`
- ✗ spun cum e organizat proiectul

**responsabilitatea: 4 din 4**

- ✓ nicio cheie în cod acum: 0 în arbore
- ✓ nicio cheie în istoric: 0 găsiri
- ✓ licență recunoscută: MIT
- ✓ urma AI în commit-uri: 34 commit-uri o declară

## Goluri — de acoperit la interviu

**metoda se schimbă după eșecuri.** Din git nu se vede: semnalul de cicatrice a ieșit la nivelul întâmplării.
> Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?

**manual sau agent, cu cost.** Din git nu se vede ce a ales omul să facă singur.
> Ce nu lăsați AI-ului să facă, deși ar putea? De ce?

## Istoricul (informație, în afara scorului)

- cicatrici: 1 din 12 modificări ale instrucțiunilor
- arhitectura ținută la zi: 5 din 5 schimbări de structură

## Ce nu se vede din fișa asta

- dacă testele sunt bune; calitatea codului; munca fără urme în git;
- un harness bogat arată un proiect pregătit pentru agent, nu că omul e bun: se poate și copia;
- licențele dependențelor; o cheie prinsă numai de forma generală (se spune lângă, nu scade).
