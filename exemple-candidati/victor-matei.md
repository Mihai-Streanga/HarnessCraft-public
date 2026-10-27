# Victor Matei · tipul 5: fișă bună, nu-și explică proiectul

*Persoană inventată: numele, profilul, proiectul și răspunsurile le-a scris agentul, pentru exemplele din manual. Orice potrivire cu o persoană reală e întâmplătoare.*

*Bifele: date de agent, la cererea autorului, după criterii și după intenția cu care a fost scris fiecare răspuns (19 octombrie 2026).*

*Cum se citește: răspunsurile și ce a predat le-a scris agentul, ca să arate tipul. Bifele le dai tu, ca recrutor: „da” sau „nu” între paranteze. Decizia de probă e tot a ta; notițele și concluzia pot rămâne goale.*

## Profilul

Absolvent de informatică (2025), un an de stagiu ca dezvoltator junior. Portofoliul: calculatorul de concedii, cu tot ce cere fișa (teste, verificări automate, reguli ținute la zi), apărut tot într-o zi, din primul commit.
Aplică pentru un post de dezvoltator junior care lucrează cu AI.

**Ce arată exemplul:** Proiectul poate să nu fie al lui. Fișa e plină, deci programul nu pune întrebări despre proiect: le pune recrutorul, la „Ale tale”. Partea IV n-are notă, dar se citește înaintea concluziei.

## II. Parcursul: CV, studii și cursuri

Note: Matematică-Informatică, absolvită în 2025; un an de stagiu la o firmă de software, pe interfețe web. Claude și Cursor le folosesc de la facultate.

## III. Întrebările cu notă

### S1. De ce lucrați cu AI? Ce urmăriți când îl folosiți?

Note: Vreau să scriu cod mai repede și să învăț pe parcurs. La stagiu, AI-ul m-a ajutat să înțeleg un cod vechi de React: i-am cerut să-mi explice componentele una câte una. Nu merită când nu știi ce vrei: atunci face mult cod pe care nu-l înțelegi.

- S1.1 [da] spune un scop concret, al lui (nu „toată lumea îl folosește”)
- S1.2 [da] dă un exemplu în care AI-ul l-a ajutat să ajungă acolo
- S1.3 [da] spune și unde AI-ul nu l-a ajutat sau nu merită folosit

### S2. Povestiți o problemă pe care ați discutat-o cu AI-ul înainte să vă apucați de lucru. Cum ați folosit conversația?

Note: Când am ales între două biblioteci de grafice la stagiu, i-am descris ce trebuie să afișăm și i-am cerut argumente pentru și contra fiecăreia, cu linkuri la documentație. Am ales-o pe cea mai mică, pentru că ne trebuiau trei tipuri de grafice; am verificat în documentație că le are.

- S2.1 [da] a lămurit întâi problema, înainte să ceară o soluție
- S2.2 [da] i-a cerut AI-ului să-l contrazică, să dea surse sau alte variante
- S2.3 [da] decizia finală a fost a lui și spune pe ce s-a bazat

### S3. Povestiți o sarcină de programare pe care ați dat-o AI-ului. Ce i-ați pregătit dinainte?

Note: La stagiu, o pagină de filtre: în tichet erau ce trebuie să facă și criteriile de acceptare; i-am cerut întâi planul, apoi codul pe bucăți. Regulile proiectului erau într-un fișier pe care Cursor îl citea la fiecare cerere.

- S3.1 [da] a scris dinainte ce vrea și cum se vede că e gata
- S3.2 [da] a împărțit lucrul în pași mici
- S3.3 [da] regulile și structura proiectului sunt scrise într-un loc pe care AI-ul îl citește de fiecare dată (AI-ul nu ține minte de la o conversație la alta)

### S4. AI-ul vă dă un rezultat și spune că e corect: o informație într-o conversație, sau un cod care „merge”. Ce faceți înainte să-l folosiți?

Note: Rulez codul și testele și citesc diff-ul. O dată mi-a dat o funcție de dată care mergea pe calculatorul meu și pica pe server, din cauza fusului orar; testele de pe server au prins-o.

- S4.1 [da] nu acceptă pe cuvânt
- S4.2 [da] verifică pe altă cale: caută sursa, rulează codul sau testele
- S4.3 [da] dă un exemplu în care așa a prins o greșeală a AI-ului

### S5. Ce nu lăsați AI-ului să facă, deși ar putea? De ce?

Note: Nu-l las să facă migrări pe baza de date și nu-i dau parole. O greșeală acolo strică datele altora; la stagiu era regula echipei, după un incident dinaintea mea.

- S5.1 [da] numește ceva concret
- S5.2 [da] motivul e riscul, costul sau o decizie care trebuie să rămână a unui om, nu doar preferința
- S5.3 [da] spune de unde știe unde e granița (o întâmplare, o măsurătoare)

### S6. Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?

Note: La început îi ceream tot codul deodată. Acum cer întâi un plan, pentru că o dată mi-a rescris jumătate de proiect pentru o schimbare mică. Am pus asta în regulile pentru Cursor.

- S6.1 [da] spune o schimbare concretă
- S6.2 [da] a pornit de la o problemă reală (o greșeală, timp pierdut)
- S6.3 [da] schimbarea e scrisă sau automată (o regulă, o verificare), nu doar ținută minte

### S7. Aveți de lucru cu date reale ale unor oameni (nume, salarii, date medicale) și vreți ajutorul AI-ului. Ce faceți?

Note: Lucrez cu date generate, false. Datele reale nu intră în AI fără acordul firmei; îl întreb pe șeful de echipă.

- S7.1 [da] nu pune datele reale în AI fără să știe unde ajung
- S7.2 [da] are o alternativă concretă: date false sau anonimizate, o unealtă aprobată de firmă
- S7.3 [da] întreabă sau anunță pe cine trebuie (șeful, clientul, regulile firmei)

## IV. Întrebările fără notă

### Ale tale

*Proiectul trece toate verificările fișei: programul nu pune întrebări despre el. Pe acestea le-a scris agentul, în rolul recrutorului.*

**Întrebarea ta 1:** Ce face verificarea din .claude/settings.json și când ați pus-o?

Note: E o setare pentru Claude, să ruleze ceva după ce modifică fișiere. Nu mai știu exact ce rulează; am văzut-o recomandată și am pus-o.

**Întrebarea ta 2:** În docs/ARHITECTURA.md scrie de ce sărbătorile stau în cod, nu într-un fișier de configurare. De ce ați ales așa?

Note: Așa a ieșit; nu m-am gândit la altă variantă. Probabil e mai simplu.

**Întrebarea ta 3:** Tot proiectul a apărut într-o zi, din primul commit. Cum l-ați lucrat?

Note: L-am lucrat pe alt calculator, fără git, și l-am urcat la sfârșit; istoricul de acolo nu-l mai am. A durat câteva seri.

## V. Încheierea

**Concluzia recrutorului:** 

## Decizia de probă (a ta)

*Tipul exemplului cere „da”; un „nu” îl schimbă, și se spune.*

**Merge la probă (da / nu):** da
**Motivul, dacă nu:** 

**Răspunsul candidatului la invitație:** a acceptat · 2026-10-08 · pe e-mail

## Proba

**Linkurile conversațiilor:** o conversație ChatGPT, textul copiat în conversatie-victor-matei.txt
**Dosarul de cod:** 

### Tabelul de răspuns predat

| Marca | Coloana | Valoarea din stat | Valoarea corecta | De ce |
|---|---|---|---|---|
| 1001 | Suma 300 lei netaxabila | 200 | 300 | Suma netaxabilă e 300 de lei. |
| 1013 | Suma ore suplimentare | 373 | 652 | Fără spor. |
| 1014 | Rest plata | 4847 | 2847 | Avansul nu e scăzut. |

### Conversațiile

*Fragmentele care contează, scrise de agent; conversația întreagă ar fi în fișierul predat.*

> **Victor:** [lipește statul] E corect statul ăsta? Ce greșeli are?
>
> **AI:** Am găsit trei probleme: la 1001, suma netaxabilă pentru salariul minim e 300 de lei, în stat apare 200; la 1013, orele suplimentare sunt plătite fără spor; la 1014, avansul nu e scăzut din restul de plată.
>
> **Victor:** Mersi. Pune-le într-un tabel cu marca, coloana, valoarea din stat și valoarea corectă.

- C1 [nu] i-a dat AI-ului statul și regulile lunii, lipite în conversație sau ca fișier, nu doar întrebarea dacă statul e corect
- C2 [nu] a cerut AI-ului de unde are o cotă sau un plafon (legea, articolul) sau a adus el sursa oficială în conversație
- C3 [nu] a contrazis AI-ul cel puțin o dată, cu ce e greșit și de ce, nu doar cu „mai verifică” sau „ești sigur?”
- C4 [nu] a făcut, cu AI-ul, un program care recalculează statul și s-a folosit de ce a ieșit (cod: în dosarul predat sau în conversație)

**Notițe despre conversații:** 

### Discuția de după predare

#### 1. Unde a greșit AI-ul în lucrul la stat?
- D1 [nu] Da, dacă: numește o greșeală anume a AI-ului (o cifră, o regulă), pe care recrutorul o găsește în conversațiile predate, nu doar „uneori greșește”
**Ce a răspuns (1):** Cred că a greșit pe la calcule, la unii, dar le-am verificat.

#### 2. Cum ai aflat cât e, în septembrie 2026, suma care nu se impozitează la salariul minim?
- D2 [nu] Da, dacă: numește o sursă oficială (ordonanța, Monitorul Oficial, legislatie.just.ro, ANAF), nu „mi-a spus AI-ul” sau „știam”
**Ce a răspuns (2):** Mi-a spus AI-ul: 300 de lei.

#### 3. Ce ai lăsat neverificat în stat, și de ce?
- D3 [nu] Da, dacă: numește ceva anume pe care nu l-a verificat și motivul (timpul, nu știa cum, nu i s-a părut important), nu „am verificat tot”
**Ce a răspuns (3):** Am verificat tot.
