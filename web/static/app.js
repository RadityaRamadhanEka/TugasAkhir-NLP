// Mengirim pertanyaan ke /api/tanya lalu menyusun kartu jawaban, kutipan halaman, dan jejak pipeline.
// Seluruh teks dari pengguna maupun korpus dimasukkan via textContent agar aman dari injeksi HTML.

const form = document.getElementById("ask-form");
const input = document.getElementById("q");
const button = document.getElementById("ask-button");
const clearBtn = document.getElementById("clear-button");
const resetHome = document.getElementById("reset-home");
const result = document.getElementById("result");

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function syncClearButton() {
  if (clearBtn) clearBtn.hidden = !input.value;
}

function pageLabel(pdf, doc) {
  if (doc && pdf) return `Halaman ${doc} buku (Hal. ${pdf} PDF)`;
  if (pdf) return `Halaman ${pdf} PDF`;
  return "Halaman tidak tercatat";
}

function shortPageLabel(pdf, doc) {
  if (doc && pdf) return `Hal. Buku ${doc} · PDF ${pdf}`;
  if (pdf) return `Hal. PDF ${pdf}`;
  return "";
}

function meter(data) {
  const pct = Math.max(0, Math.min(1, data.confidence)) * 100;
  return el("div", { class: "meter" }, [
    el("div", { class: "meter-head" }, [
      el("span", { class: "meter-score", text: `Skor Keyakinan: ${data.confidence_text}` }),
      el("span", { class: "meter-threshold", text: `Ambang minimum ${data.threshold_text}` }),
    ]),
    el("div", {
      class: "meter-track",
      role: "img",
      "aria-label": `Keyakinan ${data.confidence_text} dari 1,00 dengan ambang ${data.threshold_text}`,
    }, [
      el("div", { class: "meter-fill", style: `width:${pct}%` }),
      el("div", { class: "meter-tick", style: `left:calc(${data.threshold * 100}% - 1px)` }),
    ]),
    el("div", { class: "meter-scale", "aria-hidden": "true" }, [
      el("span", { text: "0,00" }),
      el("span", { text: `Ambang ${data.threshold_text}` }),
      el("span", { text: "1,00" }),
    ]),
  ]);
}

function withoutTitle(segments, title) {
  if (!title || !segments.length || segments[0].mark) return segments;
  const first = segments[0].text;
  if (!first.startsWith(title)) return segments;
  const rest = first.slice(title.length).replace(/^[\s:.\-–]+/, "");
  return [{ ...segments[0], text: rest }, ...segments.slice(1)].filter((s) => s.text);
}

function excerptBlock(ex) {
  const text = el("blockquote", { class: "page-text" });
  for (const seg of withoutTitle(ex.segments, ex.title)) {
    text.append(seg.mark ? el("mark", { text: seg.text }) : document.createTextNode(seg.text));
  }
  const hasMark = ex.segments.some((s) => s.mark);
  const typeLabel = (ex.content_type || "kutipan").toUpperCase();
  return el("figure", { class: "page" }, [
    el("div", { class: "page-bar" }, [
      el("span", { class: "page-bar-label", text: `Bukti Kutipan · ${typeLabel}` }),
      el("span", { class: "page-bar-loc", text: shortPageLabel(ex.pdf_page, ex.doc_page) }),
    ]),
    el("div", { class: "page-body" }, [
      ex.title ? el("p", { class: "page-title", text: ex.title }) : null,
      text,
      el("figcaption", {
        class: "page-note",
        text: `${pageLabel(ex.pdf_page, ex.doc_page)}.` +
          (hasMark ? " Bagian berstabilo kuning merupakan rentang jawaban yang diekstrak." : ""),
      }),
    ]),
  ]);
}

function answeredCard(data) {
  const srcText = data.source ? shortPageLabel(data.source.pdf_page, data.source.doc_page) : "";
  const bodyParts = [
    el("p", { class: "asked" }, ["Pertanyaan: ", el("q", { text: data.question })]),
    el("p", { class: "answer-label", text: "Jawaban Hasil Ekstraksi" }),
    el("p", {
      class: "answer-text" + (data.long_answer ? " is-long" : data.answer.length > 20 ? " is-medium" : ""),
      text: data.answer,
    }),
  ];

  if (data.source) {
    const cite = data.source.title ? el("cite", { text: data.source.title }) : null;
    bodyParts.push(el("p", { class: "citation" }, [
      "Sumber: ", cite, cite ? " — " : "", pageLabel(data.source.pdf_page, data.source.doc_page), ".",
    ]));
  }

  bodyParts.push(meter(data));
  if (data.excerpt) bodyParts.push(excerptBlock(data.excerpt));

  if (data.facts && data.facts.length) {
    bodyParts.push(el("table", { class: "fact" }, [
      el("caption", {
        text: data.facts.length > 1
          ? `${data.facts.length} triple Knowledge Base yang digabung`
          : "Triple Knowledge Base yang digunakan",
      }),
      el("thead", {}, el("tr", {}, ["Subjek", "Predikat", "Objek"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, data.facts.map((f) => el("tr", {}, [
        el("td", { text: f.subject }),
        el("td", { text: f.relation }),
        el("td", { text: f.value }),
      ]))),
    ]));
  }

  return el("article", { class: "answer-card" }, [
    el("div", { class: "card-head" }, [
      el("span", { class: "status-badge is-ok", text: "Terjawab dari Buku Pedoman" }),
      srcText ? el("span", { class: "source-pill", text: srcText }) : null,
    ]),
    el("div", { class: "card-body" }, bodyParts),
  ]);
}

function missingCard(data) {
  return el("article", { class: "answer-card is-missing" }, [
    el("div", { class: "card-head" }, [
      el("span", { class: "status-badge is-missing", text: `Ditolak Ambang (< ${data.threshold_text})` }),
      el("span", { class: "source-pill", text: "Bukti tidak mencukupi" }),
    ]),
    el("div", { class: "card-body" }, [
      el("p", { class: "asked" }, ["Pertanyaan: ", el("q", { text: data.question })]),
      el("p", { class: "answer-label", text: "Status Jawaban" }),
      el("h2", { class: "missing-title", text: "Jawabannya tidak ditemukan di buku pedoman" }),
      el("p", {
        class: "missing-why",
        text: `Kandidat terbaik hanya memperoleh keyakinan ${data.confidence_text}, di bawah batas ambang ${data.threshold_text}. ` +
          "Sistem memilih tidak menjawab daripada menebak.",
      }),
      meter(data),
      el("ul", { class: "tips" }, [
        el("li", { text: "Pastikan nama atau kode mata kuliah ditulis sesuai ejaan Kurikulum 2024." }),
        el("li", { text: "Ajukan satu topik spesifik dalam satu kalimat pertanyaan." }),
        el("li", { text: "Informasi di luar buku pedoman (nama rektor/dosen, biaya UKT, jadwal ruang) memang ditolak sistem." }),
      ]),
    ]),
  ]);
}

function featureBreakdown(candidate) {
  if (!candidate || !candidate.features || !candidate.features.length) return null;
  return el("details", { class: "feature-details" }, [
    el("summary", { text: "Rincian 8 fitur ranking + skor retrieval (kandidat #1)" }),
    el("table", { class: "feature-table" }, [
      el("thead", {}, el("tr", {}, [
        el("th", { text: "Fitur" }),
        el("th", { text: "Bobot" }),
        el("th", { text: "Nilai" }),
        el("th", { text: "B×N" }),
      ])),
      el("tbody", {}, candidate.features.map((f) => el("tr", {}, [
        el("td", { text: f.label }),
        el("td", { text: f.weight }),
        el("td", { text: f.value }),
        el("td", { text: f.weighted }),
      ]))),
    ]),
  ]);
}

function traceBlock(data) {
  const t = data.trace;
  const step = (num, title, body) => el("li", { class: "step" }, [
    el("div", { class: "step-head" }, [
      el("span", { class: "step-num", text: num }),
      el("h3", { text: title }),
    ]),
    ...body,
  ]);

  const kwNode = t.keywords && t.keywords.length
    ? el("div", { class: "kw-chips" }, t.keywords.map((k) => el("span", { class: "kw-chip", text: k })))
    : "–";

  const understood = step("01", "Analisis Pertanyaan (Modul 3)", [
    el("dl", { class: "kv-grid" }, [
      el("dt", { text: "Intent" }), el("dd", { text: t.intent || "–" }),
      el("dt", { text: "Tipe jawaban" }), el("dd", { text: t.answer_type || "–" }),
      el("dt", { text: "Fokus" }), el("dd", { text: t.focus || "–" }),
      el("dt", { text: "Entitas" }), el("dd", { text: t.entities.length ? t.entities.join(", ") : "–" }),
      el("dt", { text: "Kata kunci" }), el("dd", {}, [kwNode]),
    ]),
  ]);

  const groups = [];
  for (const p of t.passages) {
    const key = `${p.doc_page ?? p.pdf_page}|${p.content_type}|${p.title}`;
    const found = groups.find((g) => g.key === key);
    if (found) found.count += 1;
    else groups.push({ key, ...p, count: 1 });
  }

  const searched = step("02", "Retrieval Korpus & KB (Modul 4)", [
    el("p", { text: `${t.passages.length} passage teratas dan ${t.facts_found} triple tabel ditemukan.` }),
    el("ul", { class: "trace-list" }, groups.map((p) => el("li", {}, [
      `Hal. ${p.doc_page ?? p.pdf_page} (${p.content_type})`,
      p.title ? el("span", { class: "muted", text: ` — ${p.title}` }) : null,
      p.count > 1 ? el("span", { class: "muted", text: ` [${p.count}×]` }) : null,
    ]))),
  ]);

  const weighedBody = [
    el("p", { text: `${t.total_candidates} kandidat dari 4 jalur digabung & dinilai.` }),
    t.candidates.length
      ? el("ul", { class: "trace-list" }, t.candidates.map((c, i) => el("li", {
          class: "cand" + (i === 0 && data.status === "answered" ? " is-chosen" : ""),
        }, [
          el("span", { class: "cand-text", text: `${i + 1}. ${c.answer}` }),
          el("span", { class: "cand-score", text: c.score }),
          el("span", {
            class: "cand-meta",
            text: `Jalur: ${c.method}${c.sources > 1 ? ` · didukung ${c.sources} sumber (+bonus)` : ""}`,
          }),
        ])))
      : el("p", { class: "muted", text: "Tidak ada kandidat yang diekstrak." }),
  ];
  if (t.candidates.length) {
    const fb = featureBreakdown(t.candidates[0]);
    if (fb) weighedBody.push(fb);
  }
  const weighed = step("03", "4 Jalur Ekstraksi & 8 Fitur Ranking", weighedBody);

  const top = t.candidates.length ? t.candidates[0].score : "0,00";
  const decided = step("04", `Seleksi Ambang (${data.threshold_text})`, [
    data.status === "answered"
      ? el("p", { class: "decision-yes", text: `Skor tertinggi ${top} ≥ ${data.threshold_text} → Jawaban diterima.` })
      : el("p", { class: "decision-no", text: `Skor tertinggi ${top} < ${data.threshold_text} → Ditolak (tidak ditemukan).` }),
  ]);

  const timeInfo = typeof data.elapsed_ms === "number" ? `${data.elapsed_ms} ms` : "";

  return el("aside", { class: "trace-card", "aria-labelledby": "jejak" }, [
    el("div", { class: "card-head" }, [
      el("h2", { id: "jejak", class: "trace-head-title", text: "Jejak Pipeline Classic NLP" }),
      timeInfo ? el("span", { class: "trace-meta", text: timeInfo }) : null,
    ]),
    el("ol", { class: "steps" }, [understood, searched, weighed, decided]),
  ]);
}

function show(nodes) {
  result.replaceChildren(...[].concat(nodes));
  result.hidden = false;
}

async function ask(question) {
  const q = question.trim();
  if (!q) {
    input.focus();
    return;
  }

  input.value = q;
  syncClearButton();
  button.disabled = true;
  button.textContent = "Memproses…";
  result.setAttribute("aria-busy", "true");
  show(el("div", { class: "loading-box", text: "Menelusuri korpus dan menilai kandidat jawaban…" }));

  const url = new URL(window.location.href);
  url.searchParams.set("q", q);
  history.replaceState(null, "", url);

  try {
    const res = await fetch("/api/tanya", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const data = await res.json();
    if (!res.ok) {
      show(el("div", { class: "error-box", role: "alert", text: data.error || "Pertanyaan tidak dapat diproses." }));
      return;
    }
    const mainCard = data.status === "answered" ? answeredCard(data) : missingCard(data);
    show(el("div", { class: "result-grid" }, [mainCard, traceBlock(data)]));

    document.body.classList.add("is-asked");
    const page = result.querySelector(".page");
    if (page) requestAnimationFrame(() => requestAnimationFrame(() => page.classList.add("is-drawn")));
  } catch (err) {
    show(el("div", {
      class: "error-box",
      role: "alert",
      text: "Server belum merespons. Pastikan perintah python main.py --web sedang berjalan di terminal.",
    }));
  } finally {
    button.disabled = false;
    button.textContent = "Cari Jawaban";
    result.removeAttribute("aria-busy");
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  ask(input.value);
});

input.addEventListener("input", syncClearButton);

if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    input.value = "";
    syncClearButton();
    input.focus();
  });
}

if (resetHome) {
  resetHome.addEventListener("click", (e) => {
    e.preventDefault();
    input.value = "";
    syncClearButton();
    result.hidden = true;
    result.replaceChildren();
    document.body.classList.remove("is-asked");
    history.replaceState(null, "", window.location.pathname);
    input.focus();
  });
}

document.querySelectorAll(".example").forEach((btn) => {
  btn.addEventListener("click", () => ask(btn.dataset.question));
});

const initial = new URLSearchParams(window.location.search).get("q");
if (initial) ask(initial);
syncClearButton();
