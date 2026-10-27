# HarnessCraft — instalare

Pe Windows. Ce trebuie, în ordine. Versiunile sunt cele încercate; una mai nouă merge de regulă, una mai veche nu e
încercată.

| Programul | Versiunea încercată | La ce folosește |
|---|---|---|
| Python | 3.14 (cel puțin 3.12; testele pe GitHub rulează pe 3.12) | programul și testele |
| git | 2.54 | istoricul proiectelor analizate |
| gitleaks | 8.30.1 | detectorul de chei de acces (parole, tokeni) din cod și din istoric |
| pytest (în `.venv`) | 9.1 | testele |

Programul nu cheamă nimic din afara calculatorului și nu cere nicio cheie. Internetul îl folosește numai adăugarea
unui proiect dat ca link, care se clonează.

1. **Python 3.12 sau mai nou** și **git**.
   Trebuie să vezi: `py --version` → `Python 3.1x.y`; `git --version` → `git version 2.x`.
2. **gitleaks** — `winget install --id Gitleaks.Gitleaks -e`.
   Trebuie să vezi: `gitleaks version` → `8.x`, dintr-o fereastră nouă (`PATH` se citește la deschidere).
3. **Depozitul și mediul de test**:

       git clone https://github.com/Mihai-Streanga/HarnessCraft-public.git
       cd HarnessCraft-public
       py -m venv .venv
       .venv\Scripts\python -m pip install pytest
       .venv\Scripts\python -m pytest -q

   Trebuie să vezi: `… passed` și niciun `failed`. Testele sărite au motivul spus: cazul autorului, al cărui proiect e
   privat, și cele care cer fișierele rămase în depozitul privat al autorului.
4. **Aplicația**: dublu-clic pe `Porneste_HarnessCraft.bat`. Fereastra de comandă a programului pornește micșorată,
   în bara de jos; cât e deschisă, programul merge. Se deschide browserul la `http://127.0.0.1:8765`.
   Trebuie să vezi: pagina „Acasă”. Fără mediul Python (pasul 3), fereastra de comandă spune ce lipsește; fără git sau
   gitleaks, o casetă pe ecran.

Datele candidaților stau în `candidaturi/`, pe calculator; git nu le urmărește. Pentru început, ecranul „Exemple”
arată candidați inventați, cu toți pașii făcuți, numai de citit; manualul e în aplicație, la „Manualul”.
