// HarnessCraft: sapte lucruri mici, restul paginii merge si fara JavaScript.

// 1. Butoanele care dureaza (analiza unui proiect): butonul se dezactiveaza si spune ca se lucreaza,
//    ca sa nu fie apasat de doua ori.
document.querySelectorAll("form[data-lung]").forEach(function (f) {
  f.addEventListener("submit", function () {
    // butonul poate sta si in afara formularului lui (atributul form=)
    var b = f.querySelector("button") || (f.id && document.querySelector('button[form="' + f.id + '"]'));
    if (b) { b.disabled = true; b.textContent = "Se lucrează…"; }
  });
});

// 2. Interviul se salveaza singur, la fiecare bifa si la iesirea dintr-un camp de notite. Salvarile merg pe rand: una
//    pornita cat alta e pe drum asteapta si trimite starea de atunci, ca pe disc sa ramana ultima, nu cea sosita ultima.
//    Decizia de proba (data-autosalvare="decizie") se salveaza la bifa si la iesirea din motiv; fara buton: mai departe
//    duce „Pasul următor” (B24). `keepalive` lasa salvarea sa ajunga si cand omul pleaca de pe pagina chiar atunci.
document.querySelectorAll("form[data-autosalvare]").forEach(function (f) {
  var stare = f.querySelector(".stare-salvare"), peDrum = false, inca = false;
  // decizia refuzata revine la ce era salvat: butonul ales spune „hotarat” numai cand e pe disc (B9)
  var decizie = f.dataset.autosalvare === "decizie", alesSalvat = decizie && f.querySelector("input[type=radio]:checked");
  function inapoi() {
    f.querySelectorAll("input[type=radio]").forEach(function (r) { r.checked = (r === alesSalvat); });
  }
  function nuSaSalvat(motiv) {
    stare.classList.add("eroare");
    stare.textContent = "Nu s-a salvat. " + motiv.charAt(0).toUpperCase() + motiv.slice(1).replace(/\.$/, "") + ".";
    if (decizie) inapoi();
  }
  function salveaza() {
    if (peDrum) { inca = true; return; }
    peDrum = true;
    stare.textContent = "Se salvează…";
    fetch(f.action, {method: "POST", headers: {"X-Autosalvare": "1"}, keepalive: true,
                     body: new URLSearchParams(new FormData(f))})
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.salvat) return nuSaSalvat(j.eroare);
        stare.classList.remove("eroare");
        stare.textContent = "Salvat la " + new Date().toLocaleTimeString("ro-RO") + ".";
        if (decizie) alesSalvat = f.querySelector("input[type=radio]:checked");
      })
      .catch(function () { nuSaSalvat("programul nu răspunde. E pornit?"); })
      .finally(function () { peDrum = false; if (inca) { inca = false; salveaza(); } });
  }
  f.addEventListener("change", salveaza);
  // Butonul „Salvează” salveaza pe loc, fara sa reincarce pagina, si spune ora: se vede ca s-a salvat.
  if (f.dataset.autosalvare !== "decizie") f.addEventListener("submit", function (ev) { ev.preventDefault(); salveaza(); });
});

// 2b. „Alege dosarul…” / „Alege fișierul .bundle…”: fereastra Windows o deschide programul; calea vine in camp
//     (la „Candidat nou” si la programul probei, B19).
document.querySelectorAll("button[data-alege]").forEach(function (b) {
  b.addEventListener("click", function () {
    var camp = b.closest("form").querySelector("input[name=sursa], input[name=cod]");
    b.disabled = true;
    fetch("/nou/alege", {method: "POST", body: new URLSearchParams({fel: b.dataset.alege})})
      .then(function (r) { return r.json(); })
      .then(function (j) { if (j.cale) { camp.value = j.cale; camp.classList.remove("camp-gresit"); } })
      .finally(function () { b.disabled = false; });
  });
});

// 3. Selectorul de fisier e un buton al paginii („Alege fișierul”); numele fisierului ales se scrie langa el.
document.querySelectorAll(".alege-fisier input[type=file]").forEach(function (i) {
  var f = i.closest("form"), nume = f.querySelector(".nume-fisier"), trimite = f.querySelector("button");
  // „Încarcă” e activ numai dupa ce s-a ales un fisier: altfel apasarea lui nu face nimic vizibil
  trimite.disabled = !i.files.length;
  i.addEventListener("change", function () {
    nume.textContent = i.files.length ? i.files[0].name : "niciun fișier ales";
    trimite.disabled = !i.files.length;
  });
});

// 4. Linkurile lipite la „Ce a mai predat” apar pe loc ca legaturi, sub caseta lor (ca dupa o reincarcare).
document.querySelectorAll(".caseta-predata").forEach(function (f) {
  var camp = f.querySelector("textarea, input[name=cod]"), lista = f.querySelector(".linkuri");
  if (!camp || !lista) return;
  camp.addEventListener("input", function () {
    lista.replaceChildren();
    // acelasi tipar ca `_LINK` din interfata.py: linkurile, oriunde in text
    (camp.value.match(/https?:\/\/[^\s<>"']+/g) || []).forEach(function (x) {
        var a = document.createElement("a"), li = document.createElement("li");
        a.href = x; a.textContent = x; a.target = "_blank"; a.rel = "noopener noreferrer";
        li.appendChild(a); lista.appendChild(li);
      });
  });
});

// 5. O trimitere la o parte strânsă a interviului (de pildă #proiect, partea IV) o deschide.
function deschideTinta() {
  var t = location.hash && document.getElementById(location.hash.slice(1));
  for (var d = t && t.closest("details"); d; d = d.parentElement && d.parentElement.closest("details")) d.open = true;
  if (t) t.scrollIntoView();
}
deschideTinta();
window.addEventListener("hashchange", deschideTinta);

// 6. „Copiază invitația”: textul invitatiei la proba, in clipboard, ca sa fie lipit in e-mail (B36).
document.querySelectorAll("button[data-copiaza]").forEach(function (b) {
  b.addEventListener("click", function () {
    var camp = document.querySelector(b.dataset.copiaza), stare = b.nextElementSibling;
    navigator.clipboard.writeText(camp.value)
      .then(function () { stare.textContent = "Copiată. O lipești în e-mail."; })
      .catch(function () { camp.select(); stare.textContent = "Nu s-a putut copia singură: e selectată, apeși Ctrl+C."; });
  });
});
