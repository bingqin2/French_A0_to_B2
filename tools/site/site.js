// Pronunciation buttons + dictation for the French A0 → B2 site.
(function () {
  const $ = (s) => document.querySelector(s);
  const src = $("#src"), rate = $("#rate");
  src.value = localStorage.getItem("fr-src") || "google";
  rate.value = localStorage.getItem("fr-rate") || "1";
  src.onchange = () => localStorage.setItem("fr-src", src.value);
  rate.onchange = () => localStorage.setItem("fr-rate", rate.value);

  let current = null;
  function stop() {
    if (current) { current.pause(); current = null; }
    if (window.speechSynthesis) speechSynthesis.cancel();
    document.querySelectorAll("button.say.playing").forEach((b) => b.classList.remove("playing"));
  }

  function frenchVoice() {
    const vs = (window.speechSynthesis && speechSynthesis.getVoices()) || [];
    const fr = vs.filter((v) => /^fr(-|_|$)/i.test(v.lang));
    return fr.find((v) => /google/i.test(v.name)) ||
           fr.find((v) => /fr-FR/i.test(v.lang)) || fr[0] || null;
  }

  function playFile(url, btn, onFail) {
    const a = new Audio(url);
    a.playbackRate = parseFloat(rate.value);
    a.onended = () => btn && btn.classList.remove("playing");
    a.onerror = () => onFail && onFail();
    current = a;
    a.play().catch(() => onFail && onFail());
  }

  function speakBrowser(text, btn, onFail) {
    const v = frenchVoice();
    if (!v) return onFail && onFail();
    const u = new SpeechSynthesisUtterance(text);
    u.voice = v; u.lang = v.lang; u.rate = parseFloat(rate.value);
    u.onend = () => btn && btn.classList.remove("playing");
    u.onerror = () => onFail && onFail();
    speechSynthesis.speak(u);
  }

  function playMp3(btn, onFail) {
    const mp3 = btn && btn.dataset.mp3;
    if (!mp3) return onFail && onFail();
    playFile(mp3, btn, onFail);
  }

  function googleUrl(text) {
    return "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=fr&q=" +
      encodeURIComponent(text.slice(0, 200));
  }

  // Play text with the chosen source; fall back to the others if it fails.
  function say(text, btn) {
    stop();
    if (btn) btn.classList.add("playing");
    const done = () => btn && btn.classList.remove("playing");
    const order = {
      google: ["google", "browser", "mp3"],
      browser: ["browser", "google", "mp3"],
      mp3: ["mp3", "google", "browser"],
    }[src.value];
    const run = (i) => {
      if (i >= order.length) return done();
      const next = () => run(i + 1);
      if (order[i] === "google") playFile(googleUrl(text), btn, next);
      else if (order[i] === "browser") speakBrowser(text, btn, next);
      else playMp3(btn, next);
    };
    run(0);
  }

  document.addEventListener("click", (e) => {
    const b = e.target.closest("button.say");
    if (b) { e.preventDefault(); say(b.dataset.t, b); }
  });
  if (window.speechSynthesis) speechSynthesis.getVoices();  // preload voices

  // ---- Dictation (vocabulary pages) ----
  const box = $("#dictation");
  if (!box) return;
  // Importance of a word: the ⭐ cell in its row, or the ⭐ heading above its table.
  const stars = (b) => {
    const first = b.closest("tr").querySelector("td");
    let m = first && first.textContent.trim().match(/^⭐+$/);
    if (m) return m[0].length;
    let el = b.closest("table");
    while (el && (el = el.previousElementSibling || el.parentElement)) {
      if (el.tagName === "H2") { m = el.textContent.match(/⭐+/); return m ? m[0].length : 0; }
    }
    return 0;
  };
  const all = [...document.querySelectorAll("table button.say")]
    .map((b) => ({ t: b.dataset.t, btn: b, s: stars(b) }))
    .filter((w) => w.t && w.t.length < 60);
  if (!all.length) { box.remove(); return; }
  let words = all;

  box.innerHTML = `
    <h3>🎧 听写练习 Dictation</h3>
    <div>听发音，写出法语（带冠词，标点可以不写）。<i>Listen and type the French.</i></div>
    <div>练习范围 Words:
      <select id="d-tier">
        <option value="0">全部 All</option>
        <option value="3">只练 ⭐⭐⭐ 核心 Core only</option>
        <option value="2">⭐⭐ 及以上 Common + Core</option>
      </select>
    </div>
    <div>
      <button id="d-new">▶ 下一个 Next</button>
      <button id="d-again">🔁 再听 Again</button>
      <input id="d-in" placeholder="在这里输入 Type here…" autocomplete="off" autocapitalize="off" spellcheck="false">
      <button id="d-check">✔ 检查 Check</button>
      <button id="d-show">👁 答案 Answer</button>
    </div>
    <div class="result" id="d-res"></div>
    <div id="d-score" style="color:var(--muted);font-size:.9em"></div>`;
  let cur = null, right = 0, total = 0;
  const norm = (s) => s.toLowerCase().replace(/[’']/g, "'").replace(/[.,!?;:…()«»"]/g, " ")
    .replace(/\s+/g, " ").trim();
  const noAcc = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "");
  const res = $("#d-res"), inp = $("#d-in");
  const score = () => ($("#d-score").textContent = total ? `得分 Score: ${right} / ${total}` : "");

  const tierSel = $("#d-tier");
  tierSel.value = localStorage.getItem("fr-tier") || "0";
  const applyTier = () => {
    const min = parseInt(tierSel.value, 10);
    words = min ? all.filter((w) => w.s >= min) : all;
    if (!words.length) words = all;
    localStorage.setItem("fr-tier", tierSel.value);
  };
  tierSel.onchange = applyTier; applyTier();
  $("#d-new").onclick = () => {
    cur = words[Math.floor(Math.random() * words.length)];
    inp.value = ""; res.textContent = ""; inp.focus();
    say(cur.t, cur.btn);
  };
  $("#d-again").onclick = () => cur && say(cur.t, cur.btn);
  $("#d-show").onclick = () => { if (cur) res.innerHTML = `答案 Answer：<b>${cur.t}</b>`; };
  const check = () => {
    if (!cur) return;
    const a = norm(inp.value), b = norm(cur.t);
    total++;
    if (a === b) { right++; res.innerHTML = `<span class="ok">✅ 正确！${cur.t}</span>`; }
    else if (noAcc(a) === noAcc(b)) { right++; res.innerHTML = `<span class="ok">✅ 差不多！注意重音符号：<b>${cur.t}</b></span>`; }
    else res.innerHTML = `<span class="no">❌ 正确答案：<b>${cur.t}</b></span>`;
    score();
  };
  $("#d-check").onclick = check;
  inp.addEventListener("keydown", (e) => { if (e.key === "Enter") check(); });
})();
