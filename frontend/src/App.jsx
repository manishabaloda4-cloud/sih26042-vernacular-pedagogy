import { useEffect, useRef, useState } from "react";
import { health, translate, phrases, worksheet, speak } from "./api";

const TABS = [
  { id: "translate", hi: "अनुवाद", en: "Translate", note: "Type Hindi, get Punjabi" },
  { id: "live", hi: "लाइव कक्षा", en: "Live Class", note: "Speak Hindi, hear Punjabi" },
  { id: "worksheet", hi: "कार्यपत्रक", en: "Worksheets", note: "Print a bilingual sheet" },
  { id: "cards", hi: "फ्लैशकार्ड", en: "Flashcards", note: "Practise phrase by phrase" },
];

const ORIGIN = {
  verified_bank: { hi: "सत्यापित", en: "Checked by a Punjabi speaker", cls: "ok" },
  cache: { hi: "सहेजा हुआ", en: "Saved earlier, not yet checked", cls: "warn" },
  machine: { hi: "मशीन अनुवाद", en: "Machine translation, please check", cls: "warn" },
};

function Result({ r, onPlay }) {
  const o = ORIGIN[r.origin];
  return (
    <div className="result">
      <p className="pa">{r.text}</p>
      <p className={`badge ${o.cls}`}><b>{o.hi}</b> {o.en}</p>
      <button className="btn ghost" onClick={onPlay}>🔊 सुनें (Play audio)</button>
    </div>
  );
}

function Translate() {
  const [text, setText] = useState("");
  const [r, setR] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function go() {
    if (!text.trim()) return;
    setBusy(true); setErr(""); setR(null);
    try { setR(await translate(text.trim())); } catch (e) { setErr(e.message); }
    setBusy(false);
  }
  return (
    <section>
      <h2>हिंदी से पंजाबी</h2>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3}
        placeholder="यहाँ हिंदी वाक्य लिखें, जैसे: अपनी किताब खोलो" />
      <button className="btn" onClick={go} disabled={busy}>{busy ? "अनुवाद हो रहा है…" : "अनुवाद करें (Translate)"}</button>
      {err && <p className="error">{err}</p>}
      {r && <Result r={r} onPlay={() => speak(r.text).catch((e) => setErr(e.message))} />}
    </section>
  );
}

function Live() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState("");
  const [typed, setTyped] = useState("");
  const [r, setR] = useState(null);
  const [t, setT] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(hindi) {
    setBusy(true); setErr(""); setR(null); setT(null);
    const t0 = performance.now();
    try {
      const res = await translate(hindi);
      const t1 = performance.now();
      setR(res);
      let audio = null;
      try { audio = await speak(res.text); } catch (e) { setErr(e.message); }
      setT({ translate: t1 - t0, audio, total: performance.now() - t0 });
    } catch (e) { setErr(e.message); }
    setBusy(false);
  }

  function toggle() {
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = "hi-IN"; rec.interimResults = true; rec.continuous = false;
    let finalText = "";
    rec.onresult = (e) => {
      let s = "";
      for (let i = 0; i < e.results.length; i++) s += e.results[i][0].transcript;
      finalText = s; setHeard(s);
    };
    rec.onerror = (e) => setErr(`Microphone problem: ${e.error}. Allow microphone access in the browser.`);
    rec.onend = () => { setListening(false); if (finalText.trim()) run(finalText.trim()); };
    recRef.current = rec; setHeard(""); setErr(""); rec.start(); setListening(true);
  }

  const fast = t && t.audio !== null && t.total < 3000;
  return (
    <section>
      <h2>लाइव कक्षा</h2>
      <div className="board">
        <div className={`clock ${t ? (fast ? "fast" : "slow") : ""}`}>{t ? (t.total / 1000).toFixed(2) : "0.00"}<small> सेकंड</small></div>
        {t ? (
          <ul>
            <li><span>अनुवाद (Translation)</span><b>{Math.round(t.translate)} ms</b></li>
            <li><span>आवाज़ शुरू (Audio start)</span><b>{t.audio === null ? "failed" : `${Math.round(t.audio)} ms`}</b></li>
          </ul>
        ) : <p className="chalk">लक्ष्य: 3 सेकंड से कम (Goal: under 3 seconds). Speech recognition runs in the browser and is not counted.</p>}
      </div>

      {SR ? (
        <button className={`mic ${listening ? "on" : ""}`} onClick={toggle} disabled={busy}>
          {listening ? "रोकें (Stop)" : busy ? "…" : "🎙️ बोलिए (Speak)"}
        </button>
      ) : <p className="error">This browser has no speech recognition. Use Chrome or Edge, or type below.</p>}
      {heard && <p className="heard"><b>सुना:</b> {heard}</p>}

      <div className="row">
        <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="या यहाँ लिखें (or type)"
          onKeyDown={(e) => e.key === "Enter" && typed.trim() && run(typed.trim())} />
        <button className="btn" disabled={busy || !typed.trim()} onClick={() => run(typed.trim())}>भेजें (Send)</button>
      </div>
      {err && <p className="error">{err}</p>}
      {r && <Result r={r} onPlay={() => speak(r.text).catch((e) => setErr(e.message))} />}
    </section>
  );
}

const CATS = [["", "सभी (All)"], ["classroom_instruction", "Classroom instructions"], ["numeracy", "Numeracy"],
  ["literacy", "Literacy"], ["praise", "Praise"], ["encouragement", "Encouragement"], ["activity", "Activity"],
  ["conversation", "Conversation"], ["check_understanding", "Check understanding"]];

function Worksheet() {
  const [grade, setGrade] = useState("");
  const [category, setCategory] = useState("");
  const [count, setCount] = useState(10);
  const [w, setW] = useState(null);
  const [err, setErr] = useState("");

  async function make() {
    setErr("");
    try { setW(await worksheet({ grade, category, count })); } catch (e) { setErr(e.message); }
  }
  return (
    <section>
      <h2>द्विभाषी कार्यपत्रक</h2>
      <div className="row wrap no-print">
        <label>कक्षा (Grade)
          <select value={grade} onChange={(e) => setGrade(e.target.value)}>
            <option value="">सभी (All)</option><option>1</option><option>2</option><option>3</option>
          </select></label>
        <label>विषय (Topic)
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select></label>
        <label>संख्या (Items)
          <input type="number" min="1" max="30" value={count} onChange={(e) => setCount(e.target.value)} /></label>
      </div>
      <div className="row no-print">
        <button className="btn" onClick={make}>बनाएँ (Create)</button>
        {w && w.items.length > 0 && <button className="btn ghost" onClick={() => window.print()}>प्रिंट / PDF (Print or save as PDF)</button>}
      </div>
      {err && <p className="error">{err}</p>}
      {w && (w.items.length === 0
        ? <p className="muted">इस चयन के लिए कोई वाक्य नहीं मिला (No phrases match this choice).</p>
        : <div className="sheet">
            <h3>द्विभाषी कार्यपत्रक (Bilingual Worksheet)</h3>
            <p>नाम (Name): ____________________ &nbsp; दिनांक (Date): ______________</p>
            <p>हर हिंदी वाक्य पढ़ें और पंजाबी में दोहराएँ। (Read each Hindi sentence and repeat it in Punjabi.)</p>
            <table><thead><tr><th>#</th><th>हिंदी</th><th>ਪੰਜਾਬੀ</th></tr></thead>
              <tbody>{w.items.map((it) => (
                <tr key={it.n}><td>{it.n}</td><td>{it.hindi}</td><td className="pa-sm">{it.target_text}</td></tr>))}</tbody></table>
            {w.items.some((i) => !i.verified) && <p className="muted small">Some translations have not been checked by a Punjabi speaker yet.</p>}
          </div>)}
    </section>
  );
}

function Cards() {
  const [list, setList] = useState([]);
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { phrases({ limit: 100 }).then((d) => setList(d.phrases)).catch((e) => setErr(e.message)); }, []);
  const c = list[i];
  const go = (d) => { setFlip(false); setI((i + d + list.length) % list.length); };
  return (
    <section>
      <h2>फ्लैशकार्ड</h2>
      {err && <p className="error">{err}</p>}
      {!c && !err && <p className="muted">कोई कार्ड नहीं (No cards yet). Load phrases into the backend first.</p>}
      {c && (<>
        <button className={`card ${flip ? "back" : ""}`} onClick={() => setFlip(!flip)} aria-label="Flip card">
          <span className={flip ? "pa" : "hi"}>{flip ? c.target_text : c.hindi}</span>
          <small>{flip ? "ਪੰਜਾਬੀ" : "हिंदी"} (tap to flip)</small>
        </button>
        <div className="row">
          <button className="btn ghost" onClick={() => go(-1)}>पीछे (Back)</button>
          <button className="btn ghost" onClick={() => speak(c.target_text).catch((e) => setErr(e.message))}>🔊 सुनें</button>
          <button className="btn ghost" onClick={() => go(1)}>आगे (Next)</button>
        </div>
        <p className="muted center">{i + 1} / {list.length}</p>
      </>)}
    </section>
  );
}

const SCREENS = { translate: Translate, live: Live, worksheet: Worksheet, cards: Cards };

export default function App() {
  const [tab, setTab] = useState("home");
  const [online, setOnline] = useState(null);
  useEffect(() => { health().then(() => setOnline(true)).catch(() => setOnline(false)); }, []);
  const Screen = SCREENS[tab];
  return (
    <div className="app">
      <header className="no-print">
        <button className="brand" onClick={() => setTab("home")}>कक्षा सेतु <small>Classroom Bridge</small></button>
        <span className={`dot ${online === null ? "" : online ? "up" : "down"}`}>
          {online === null ? "जाँच…" : online ? "सर्वर जुड़ा" : "सर्वर बंद"}</span>
      </header>
      {online === false && <p className="error">Cannot reach the server. Start the backend (python -m uvicorn app.main:app --reload) and refresh.</p>}
      <main>
        {tab === "home" ? (
          <>
            <h1>हिंदी में पढ़ाइए, बच्चे पंजाबी में समझेंगे</h1>
            <p className="muted">Teach in Hindi and children hear it in Punjabi.</p>
            <div className="menu">{TABS.map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}><b>{t.hi}</b><span>{t.en}</span><small>{t.note}</small></button>))}
            </div>
          </>
        ) : (
          <>
            <nav className="tabs no-print">{TABS.map((t) => (
              <button key={t.id} className={t.id === tab ? "on" : ""} onClick={() => setTab(t.id)}>{t.hi}</button>))}
            </nav>
            <Screen />
          </>
        )}
      </main>
    </div>
  );
}
