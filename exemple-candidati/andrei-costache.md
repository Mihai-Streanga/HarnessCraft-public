# Andrei Costache · tipul 3: cu cod, dar la probă numai conversații

*Persoană inventată: numele, profilul, proiectul și răspunsurile le-a scris agentul, pentru exemplele din manual. Orice potrivire cu o persoană reală e întâmplătoare.*

*Bifele: date de agent, la cererea autorului, după criterii și după intenția cu care a fost scris fiecare răspuns (19 octombrie 2026).*

*Cum se citește: răspunsurile și ce a predat le-a scris agentul, ca să arate tipul. Bifele le dai tu, ca recrutor: „da” sau „nu” între paranteze. Decizia de probă e tot a ta; notițele și concluzia pot rămâne goale.*

## Profilul

Analist financiar, 5 ani, la o firmă de servicii; de doi ani automatizează rapoarte în Python. Portofoliul: calculatorul de concedii, făcut cu Claude Code pentru colegii de la HR.
Aplică pentru un post de analist cu automatizări în HR.

**Ce arată exemplul:** Proba merge și fără cod: a lucrat numai în chat, deci fișa probei lipsește; ea nu are notă, iar nota probei se face din tabel, conversații și discuție.

## II. Parcursul: CV, studii și cursuri

Note: Finanțe-Bănci la ASE, apoi 5 ani analist financiar. Python am învățat singur, apoi cu un curs online acum doi ani; Claude Code îl folosesc de un an, la serviciu și acasă.

## III. Întrebările cu notă

### S1. De ce lucrați cu AI? Ce urmăriți când îl folosiți?

Note: Vreau să fac în două ore rapoarte care îmi luau o zi. Raportul lunar de costuri pe departamente îl scot acum dintr-un script făcut cu Claude Code; înainte îl copiam de mână din trei exporturi. Nu merită pentru lucruri pe care le fac o singură dată: până îi explic, le-am terminat.

- S1.1 [da] spune un scop concret, al lui (nu „toată lumea îl folosește”)
- S1.2 [da] dă un exemplu în care AI-ul l-a ajutat să ajungă acolo
- S1.3 [da] spune și unde AI-ul nu l-a ajutat sau nu merită folosit

### S2. Povestiți o problemă pe care ați discutat-o cu AI-ul înainte să vă apucați de lucru. Cum ați folosit conversația?

Note: Înainte de calculatorul de concedii l-am întrebat cum se numără zilele de concediu: lucrătoare sau calendaristice, ce se întâmplă cu sărbătorile. I-am cerut articolele din Codul muncii, nu doar răspunsul; mi-a dat art. 139 pentru sărbători. L-am citit și am hotărât să număr numai zilele lucrătoare, pentru că așa le numără și formularul firmei.

- S2.1 [da] a lămurit întâi problema, înainte să ceară o soluție
- S2.2 [da] i-a cerut AI-ului să-l contrazică, să dea surse sau alte variante
- S2.3 [da] decizia finală a fost a lui și spune pe ce s-a bazat

### S3. Povestiți o sarcină de programare pe care ați dat-o AI-ului. Ce i-ați pregătit dinainte?

Note: Verificarea cererii peste sold. În CLAUDE.md erau deja regulile proiectului, comanda de teste și ce nu are voie să schimbe. Pentru sarcină am scris ce vreau: o funcție care întoarce motivul refuzului, și un test cu o cerere de 10 zile când mai sunt 5. Am lucrat pe pași: întâi testul, apoi funcția.

- S3.1 [da] a scris dinainte ce vrea și cum se vede că e gata
- S3.2 [da] a împărțit lucrul în pași mici
- S3.3 [da] regulile și structura proiectului sunt scrise într-un loc pe care AI-ul îl citește de fiecare dată (AI-ul nu ține minte de la o conversație la alta)

### S4. AI-ul vă dă un rezultat și spune că e corect: o informație într-o conversație, sau un cod care „merge”. Ce faceți înainte să-l folosiți?

Note: Rulez testele. La o informație cer sursa și o deschid. O dată mi-a scris un test care trecea mereu, pentru că verifica funcția cu ea însăși; l-am prins pentru că testul a trecut înainte să existe codul.

- S4.1 [da] nu acceptă pe cuvânt
- S4.2 [da] verifică pe altă cale: caută sursa, rulează codul sau testele
- S4.3 [da] dă un exemplu în care așa a prins o greșeală a AI-ului

### S5. Ce nu lăsați AI-ului să facă, deși ar putea? De ce?

Note: Nu-l las să facă singur commit sau push și nu-i dau datele reale ale colegilor. Commit-ul îl citesc eu, rând cu rând: o dată mi-a șters un fișier de configurare la o „curățenie” pe care n-o cerusem.

- S5.1 [da] numește ceva concret
- S5.2 [da] motivul e riscul, costul sau o decizie care trebuie să rămână a unui om, nu doar preferința
- S5.3 [da] spune de unde știe unde e granița (o întâmplare, o măsurătoare)

### S6. Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?

Note: La început îi explicam proiectul de fiecare dată. Am pus regulile în CLAUDE.md după ce a schimbat de două ori lista de sărbători fără sursă; acum regula e scrisă acolo.

- S6.1 [da] spune o schimbare concretă
- S6.2 [da] a pornit de la o problemă reală (o greșeală, timp pierdut)
- S6.3 [da] schimbarea e scrisă sau automată (o regulă, o verificare), nu doar ținută minte

### S7. Aveți de lucru cu date reale ale unor oameni (nume, salarii, date medicale) și vreți ajutorul AI-ului. Ce faceți?

Note: Lucrez pe date false: am făcut un fișier cu angajați inventați. Datele reale nu ies din sistemul de HR; dacă ar trebui, o întreb întâi pe șefa mea și pe colegul de la IT ce unealtă e aprobată.

- S7.1 [da] nu pune datele reale în AI fără să știe unde ajung
- S7.2 [da] are o alternativă concretă: date false sau anonimizate, o unealtă aprobată de firmă
- S7.3 [da] întreabă sau anunță pe cine trebuie (șeful, clientul, regulile firmei)

## IV. Întrebările fără notă

### Despre proiectul lui

*Le-a ales programul; textul, din ghidul lui.*

**1.** Codul nu e verificat automat pe un server de fiecare dată când îl trimiteți: nimic nu rulează testele singur, fără să-și amintească cineva (integrare continuă, CI). Cine verifică codul înainte să ajungă la alții, și când?

*Ce afli: dacă verificarea depinde de memoria omului sau rulează singură.*

Note: Nimeni, în afară de mine: rulez testele înainte de commit, când îmi amintesc. Recunosc că am uitat de câteva ori.

**2.** Cât lucrează AI-ul, nu rulează nicio verificare automată care să-l oprească dacă greșește (hooks de agent). Cum aflați că AI-ul a greșit, înainte ca greșeala să rămână în proiect?

*Ce afli: dacă omul supraveghează AI-ul pe parcurs sau doar la sfârșit.*

Note: Citesc diff-ul la sfârșit. Pe parcurs n-am nimic care să-l oprească; mă bazez pe faptul că văd eu.

## V. Încheierea

**Concluzia recrutorului:** 

## Decizia de probă (a ta)

*Tipul exemplului cere „da”; un „nu” îl schimbă, și se spune.*

**Merge la probă (da / nu):** da
**Motivul, dacă nu:** 

**Răspunsul candidatului la invitație:** a acceptat · 2026-10-07 · pe e-mail

## Proba

**Linkurile conversațiilor:** o conversație Claude, textul copiat în conversatie-andrei-costache.txt
**Dosarul de cod:** 

### Tabelul de răspuns predat

| Marca | Coloana | Valoarea din stat | Valoarea corecta | De ce |
|---|---|---|---|---|
| 1014 | Rest plata | 4847 | 2847 | Avansul nu e scăzut. |
| 1013 | Suma ore suplimentare | 373 | 652 | Orele suplimentare fără spor. |
| 1002 | Suma 300 lei netaxabila | 300 | 200 | Din iulie e 200 de lei. |
| 1010 | Suma ore suplimentare | 430 | 469 | Calcul greșit al orelor suplimentare. |

### Conversațiile

*Fragmentele care contează, scrise de agent; conversația întreagă ar fi în fișierul predat.*

> **Andrei:** [lipește statul și mesajul probei] Găsește greșelile de calcul din statul ăsta.
>
> **AI:** Am găsit: 1014, avansul nu e scăzut; 1013, orele suplimentare fără spor; 1002, suma netaxabilă de 300 de lei, din iulie e 200; 1010, orele suplimentare par calculate greșit, ar trebui 469 de lei.
>
> **Andrei:** Ești sigur la 1010? Mai verifică.
>
> **AI:** Da, am recalculat: 469 de lei.
>
> **Andrei:** Ok. Mai e ceva?
>
> **AI:** Restul statului pare în regulă.

- C1 [da] i-a dat AI-ului statul și regulile lunii, lipite în conversație sau ca fișier, nu doar întrebarea dacă statul e corect
- C2 [nu] a cerut AI-ului de unde are o cotă sau un plafon (legea, articolul) sau a adus el sursa oficială în conversație
- C3 [nu] a contrazis AI-ul cel puțin o dată, cu ce e greșit și de ce, nu doar cu „mai verifică” sau „ești sigur?”
- C4 [nu] a făcut, cu AI-ul, un program care recalculează statul și s-a folosit de ce a ieșit (cod: în dosarul predat sau în conversație)

**Notițe despre conversații:** 

### Discuția de după predare

#### 1. Unde a greșit AI-ul în lucrul la stat?
- D1 [nu] Da, dacă: numește o greșeală anume a AI-ului (o cifră, o regulă), pe care recrutorul o găsește în conversațiile predate, nu doar „uneori greșește”
**Ce a răspuns (1):** La 1010 a dat o cifră și, când am întrebat, a confirmat-o; altă greșeală nu-mi vine acum. Uneori mai amesteca coloanele.

#### 2. Cum ai aflat cât e, în septembrie 2026, suma care nu se impozitează la salariul minim?
- D2 [nu] Da, dacă: numește o sursă oficială (ordonanța, Monitorul Oficial, legislatie.just.ro, ANAF), nu „mi-a spus AI-ul” sau „știam”
**Ce a răspuns (2):** Mi-a spus AI-ul că din iulie e 200 de lei și am văzut același lucru pe un site de contabilitate.

#### 3. Ce ai lăsat neverificat în stat, și de ce?
- D3 [da] Da, dacă: numește ceva anume pe care nu l-a verificat și motivul (timpul, nu știa cum, nu i s-a părut important), nu „am verificat tot”
**Ce a răspuns (3):** Impozitul: nu l-am verificat la nimeni, pentru că am avut două ore și am mers pe ce a găsit AI-ul.
