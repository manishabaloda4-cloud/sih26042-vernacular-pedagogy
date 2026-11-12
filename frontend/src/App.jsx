import { useEffect, useRef, useState } from "react";
import { health, translate, phrases, worksheet, speak } from "./api";
import "./App.css";

const TABS = [
  {
    id: "translate",
    hi: "अनुवाद",
    en: "Translate",
    note: "Hindi → Punjabi",
    icon: "↔",
  },
  {
    id: "live",
    hi: "लाइव कक्षा",
    en: "Live Class",
    note: "Speak Hindi, hear Punjabi",
    icon: "🎙️",
  },
  {
    id: "worksheet",
    hi: "कार्यपत्रक",
    en: "Worksheets",
    note: "Create bilingual sheets",
    icon: "📄",
  },
  {
    id: "cards",
    hi: "फ्लैशकार्ड",
    en: "Flashcards",
    note: "Practice phrase by phrase",
    icon: "🧠",
  },
];

const ORIGIN = {
  verified_bank: {
    hi: "सत्यापित अनुवाद",
    en: "Checked by a Punjabi speaker",
    cls: "ok",
  },
  cache: {
    hi: "सहेजा हुआ",
    en: "Saved earlier, not yet checked",
    cls: "warn",
  },
  machine: {
    hi: "मशीन अनुवाद",
    en: "Please check this translation",
    cls: "warn",
  },
};

function Result({ r, onPlay }) {
  const o = ORIGIN[r.origin] || ORIGIN.machine;

  return (
    <div className="result-card">
      <div className="result-label">
        <span>Punjabi Translation</span>
        <span className="confidence">
          {Math.round(r.confidence || 100)}% confidence
        </span>
      </div>

      <p className="pa-result">{r.text}</p>

      <div className={`translation-status ${o.cls}`}>
        <span>{o.cls === "ok" ? "✓" : "!"}</span>
        <div>
          <b>{o.hi}</b>
          <small>{o.en}</small>
        </div>
      </div>

      <button className="audio-button" onClick={onPlay}>
        🔊 Listen to Punjabi
      </button>
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

    setBusy(true);
    setErr("");
    setR(null);

    try {
      setR(await translate(text.trim()));
    } catch (e) {
      setErr(e.message);
    }

    setBusy(false);
  }

  function useExample(value) {
    setText(value);
    setR(null);
    setErr("");
  }

  return (
    <section className="workspace">
      <div className="section-heading">
        <div>
          <span className="eyebrow">TRANSLATION TOOL</span>
          <h2>Hindi to Punjabi</h2>
          <p>हिंदी में लिखें और तुरंत पंजाबी अनुवाद पाएं।</p>
        </div>
        <div className="language-flow">
          <span>🇮🇳 Hindi</span>
          <span>→</span>
          <span>🟣 Punjabi</span>
        </div>
      </div>

      <div className="translator-grid">
        <div className="input-panel">
          <div className="panel-top">
            <div>
              <span className="language-title">🇮🇳 Hindi</span>
              <small>हिंदी</small>
            </div>

            <span className="live-badge">● Ready</span>
          </div>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder="यहाँ हिंदी वाक्य लिखें..."
          />

          <div className="character-count">
            {text.length} characters
          </div>

          <div className="examples">
            <span>Try an example:</span>

            <button onClick={() => useExample("सुप्रभात बच्चों")}>
              सुप्रभात बच्चों
            </button>

            <button
              onClick={() =>
                useExample("आज हम कक्षा में एक नया पाठ पढ़ेंगे")
              }
            >
              आज हम नया पाठ पढ़ेंगे
            </button>
          </div>

          <button
            className="translate-button"
            onClick={go}
            disabled={busy || !text.trim()}
          >
            {busy ? (
              <>
                <span className="spinner"></span>
                Translating...
              </>
            ) : (
              <>✨ Translate to Punjabi</>
            )}
          </button>
        </div>

        <div className="output-panel">
          <div className="panel-top">
            <div>
              <span className="language-title">🟣 Punjabi</span>
              <small>ਪੰਜਾਬੀ</small>
            </div>
            <span className="output-label">OUTPUT</span>
          </div>

          {!r && !err && (
            <div className="empty-result">
              <div className="empty-icon">文</div>
              <h3>Your translation will appear here</h3>
              <p>
                Enter a Hindi sentence on the left and click Translate.
              </p>
            </div>
          )}

          {busy && (
            <div className="empty-result">
              <div className="loading-orb">✨</div>
              <h3>Translating your sentence...</h3>
              <p>Please wait a moment.</p>
            </div>
          )}

          {err && <div className="error-box">⚠️ {err}</div>}

          {r && !busy && (
            <Result
              r={r}
              onPlay={() =>
                speak(r.text).catch((e) => setErr(e.message))
              }
            />
          )}
        </div>
      </div>

      <div className="feature-strip">
        <div>
          <span>✓</span>
          <div>
            <b>Classroom Ready</b>
            <small>Designed for teachers</small>
          </div>
        </div>

        <div>
          <span>🔊</span>
          <div>
            <b>Audio Support</b>
            <small>Listen to Punjabi pronunciation</small>
          </div>
        </div>

        <div>
          <span>⚡</span>
          <div>
            <b>Fast & Simple</b>
            <small>Minimal steps for classroom use</small>
          </div>
        </div>
      </div>
    </section>
  );
}

function Live() {
  const SR =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  const recRef = useRef(null);

  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState("");
  const [typed, setTyped] = useState("");
  const [r, setR] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(hindi) {
    setBusy(true);
    setErr("");
    setR(null);

    try {
      const result = await translate(hindi);
      setR(result);

      try {
        await speak(result.text);
      } catch (e) {
        setErr(e.message);
      }
    } catch (e) {
      setErr(e.message);
    }

    setBusy(false);
  }

  function toggle() {
    if (!SR) return;

    if (listening) {
      recRef.current?.stop();
      return;
    }

    const rec = new SR();

    rec.lang = "hi-IN";
    rec.interimResults = true;
    rec.continuous = false;

    let finalText = "";

    rec.onresult = (e) => {
      let s = "";

      for (let i = 0; i < e.results.length; i++) {
        s += e.results[i][0].transcript;
      }

      finalText = s;
      setHeard(s);
    };

    rec.onerror = (e) => {
      setErr(
        `Microphone problem: ${e.error}. Please allow microphone access.`
      );
    };

    rec.onend = () => {
      setListening(false);

      if (finalText.trim()) {
        run(finalText.trim());
      }
    };

    recRef.current = rec;
    setHeard("");
    setErr("");
    rec.start();
    setListening(true);
  }

  return (
    <section className="workspace">
      <div className="section-heading">
        <div>
          <span className="eyebrow">LIVE CLASSROOM</span>
          <h2>Speak Hindi. Hear Punjabi.</h2>
          <p>
            बोलिए हिंदी में और पंजाबी में तुरंत सुनिए।
          </p>
        </div>
      </div>

      <div className="live-card">
        <div className="microphone-circle">
          {listening ? "🔴" : "🎙️"}
        </div>

        <h3>
          {listening
            ? "Listening..."
            : busy
            ? "Translating..."
            : "Ready for your voice"}
        </h3>

        <p>
          {listening
            ? "Speak your Hindi sentence clearly."
            : "Press the microphone and start speaking."}
        </p>

        <button
          className={`mic-button ${listening ? "recording" : ""}`}
          onClick={toggle}
          disabled={busy}
        >
          {listening ? "Stop Listening" : "Start Speaking"}
        </button>

        {heard && (
          <div className="heard-box">
            <small>You said</small>
            <p>{heard}</p>
          </div>
        )}
      </div>

      <div className="manual-input">
        <span>Prefer typing?</span>

        <div className="row">
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="हिंदी वाक्य यहाँ लिखें..."
            onKeyDown={(e) =>
              e.key === "Enter" &&
              typed.trim() &&
              run(typed.trim())
            }
          />

          <button
            className="translate-button compact"
            disabled={busy || !typed.trim()}
            onClick={() => run(typed.trim())}
          >
            Send →
          </button>
        </div>
      </div>

      {err && <div className="error-box">⚠️ {err}</div>}

      {r && (
        <Result
          r={r}
          onPlay={() =>
            speak(r.text).catch((e) => setErr(e.message))
          }
        />
      )}
    </section>
  );
}

const CATS = [
  ["", "All"],
  ["classroom_instruction", "Classroom instructions"],
  ["numeracy", "Numeracy"],
  ["literacy", "Literacy"],
  ["praise", "Praise"],
  ["encouragement", "Encouragement"],
  ["activity", "Activity"],
  ["conversation", "Conversation"],
  ["check_understanding", "Check understanding"],
];

function Worksheet() {
  const [grade, setGrade] = useState("");
  const [category, setCategory] = useState("");
  const [count, setCount] = useState(10);
  const [w, setW] = useState(null);
  const [err, setErr] = useState("");

  async function make() {
    setErr("");

    try {
      setW(await worksheet({ grade, category, count }));
    } catch (e) {
      setErr(e.message);
    }
  }

  return (
    <section className="workspace">
      <div className="section-heading">
        <div>
          <span className="eyebrow">TEACHING MATERIAL</span>
          <h2>Bilingual Worksheets</h2>
          <p>
            हिंदी और पंजाबी में कक्षा के लिए कार्यपत्रक बनाएं।
          </p>
        </div>
      </div>

      <div className="controls-card">
        <label>
          <span>Grade</span>

          <select
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
          >
            <option value="">All grades</option>
            <option value="1">Grade 1</option>
            <option value="2">Grade 2</option>
            <option value="3">Grade 3</option>
          </select>
        </label>

        <label>
          <span>Topic</span>

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Items</span>

          <input
            type="number"
            min="1"
            max="30"
            value={count}
            onChange={(e) => setCount(e.target.value)}
          />
        </label>

        <button className="translate-button" onClick={make}>
          ✨ Create Worksheet
        </button>
      </div>

      {err && <div className="error-box">⚠️ {err}</div>}

      {w &&
        (w.items.length === 0 ? (
          <div className="empty-card">
            <h3>No matching phrases</h3>
            <p>
              Try another grade or topic.
            </p>
          </div>
        ) : (
          <div className="worksheet-card">
            <div className="worksheet-header">
              <div>
                <span className="eyebrow">CLASSROOM BRIDGE</span>
                <h3>Bilingual Worksheet</h3>
                <p>कक्षा सेतु • हिंदी → पंजाबी</p>
              </div>

              <button
                className="print-button no-print"
                onClick={() => window.print()}
              >
                🖨 Print / PDF
              </button>
            </div>

            <div className="student-info">
              <span>Name: ____________________</span>
              <span>Date: ______________</span>
            </div>

            <p className="worksheet-instruction">
              Read each Hindi sentence and repeat it in Punjabi.
              <br />
              प्रत्येक हिंदी वाक्य पढ़ें और उसे पंजाबी में दोहराएँ।
            </p>

            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Hindi</th>
                  <th>Punjabi</th>
                </tr>
              </thead>

              <tbody>
                {w.items.map((it) => (
                  <tr key={it.n}>
                    <td>{it.n}</td>
                    <td>{it.hindi}</td>
                    <td>{it.target_text}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {w.items.some((i) => !i.verified) && (
              <p className="worksheet-note">
                Some translations have not been checked by a Punjabi
                speaker yet.
              </p>
            )}
          </div>
        ))}
    </section>
  );
}

function Cards() {
  const [list, setList] = useState([]);
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    phrases({ limit: 100 })
      .then((d) => setList(d.phrases))
      .catch((e) => setErr(e.message));
  }, []);

  const c = list[i];

  function go(direction) {
    if (!list.length) return;

    setFlip(false);

    setI(
      (i + direction + list.length) % list.length
    );
  }

  return (
    <section className="workspace">
      <div className="section-heading">
        <div>
          <span className="eyebrow">PRACTICE</span>
          <h2>Classroom Flashcards</h2>
          <p>
            वाक्य को याद करें और पंजाबी में बोलने का अभ्यास करें।
          </p>
        </div>
      </div>

      {err && <div className="error-box">⚠️ {err}</div>}

      {!c && !err && (
        <div className="empty-card">
          <div className="empty-icon">🧠</div>
          <h3>No flashcards yet</h3>
          <p>Load phrases into the backend first.</p>
        </div>
      )}

      {c && (
        <>
          <div
            className={`flashcard ${flip ? "flipped" : ""}`}
            onClick={() => setFlip(!flip)}
          >
            <div className="flashcard-inner">
              <div className="flashcard-front">
                <span>🇮🇳 Hindi</span>
                <strong>{c.hindi}</strong>
                <small>Tap to reveal Punjabi</small>
              </div>

              <div className="flashcard-back">
                <span>🟣 Punjabi</span>
                <strong>{c.target_text}</strong>
                <small>Tap to flip back</small>
              </div>
            </div>
          </div>

          <div className="card-controls">
            <button
              className="secondary-button"
              onClick={() => go(-1)}
            >
              ← Back
            </button>

            <button
              className="audio-button"
              onClick={() =>
                speak(c.target_text).catch((e) =>
                  setErr(e.message)
                )
              }
            >
              🔊 Listen
            </button>

            <button
              className="secondary-button"
              onClick={() => go(1)}
            >
              Next →
            </button>
          </div>

          <p className="progress">
            {i + 1} / {list.length}
          </p>
        </>
      )}
    </section>
  );
}

const SCREENS = {
  translate: Translate,
  live: Live,
  worksheet: Worksheet,
  cards: Cards,
};

export default function App() {
  const [tab, setTab] = useState("home");
  const [online, setOnline] = useState(null);

  useEffect(() => {
    health()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

  const Screen = SCREENS[tab];

  return (
    <div className="app">
      <header className="topbar">
        <button
          className="brand"
          onClick={() => setTab("home")}
        >
          <span className="brand-mark">क</span>

          <span>
            <b>कक्षा सेतु</b>
            <small>Classroom Bridge</small>
          </span>
        </button>

        <div className="server-status">
          <span
            className={`status-dot ${
              online === null
                ? "checking"
                : online
                ? "online"
                : "offline"
            }`}
          ></span>

          {online === null
            ? "Checking server..."
            : online
            ? "Server Connected"
            : "Server Offline"}
        </div>
      </header>

      {online === false && (
        <div className="server-warning">
          ⚠️ Cannot reach the translation server.
        </div>
      )}

      <main className="main">
        {tab === "home" ? (
          <>
            <section className="hero">
              <div className="hero-content">
                <div className="hero-badge">
                  🌐 Bilingual Classroom Technology
                </div>

                <h1>
                  Language should never be a barrier to learning.
                </h1>

                <p className="hero-hi">
                  भाषा कभी भी सीखने में बाधा नहीं बननी चाहिए।
                </p>

                <p className="hero-description">
                  Help teachers communicate naturally across Hindi
                  and Punjabi with simple translation, voice,
                  worksheets and learning tools.
                </p>

                <button
                  className="hero-button"
                  onClick={() => setTab("translate")}
                >
                  Start Translating →
                </button>
              </div>

              <div className="hero-visual">
                <div className="floating-card card-one">
                  <span>🇮🇳</span>
                  <div>
                    <small>Teacher says</small>
                    <b>सुप्रभात बच्चों</b>
                  </div>
                </div>

                <div className="translation-arrow">↓</div>

                <div className="floating-card card-two">
                  <span>🟣</span>
                  <div>
                    <small>Students hear</small>
                    <b>ਸ਼ੁਭ ਸਵੇਰ ਦੇ ਬੱਚੇ</b>
                  </div>
                </div>

                <div className="orb orb-one"></div>
                <div className="orb orb-two"></div>
              </div>
            </section>

            <section className="tools-section">
              <div className="section-title">
                <div>
                  <span className="eyebrow">CLASSROOM TOOLS</span>
                  <h2>Everything a teacher needs</h2>
                </div>

                <p>
                  Simple tools designed for real classroom use.
                </p>
              </div>

              <div className="tool-grid">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    className="tool-card"
                    onClick={() => setTab(t.id)}
                  >
                    <div className="tool-icon">{t.icon}</div>

                    <div>
                      <span className="tool-hi">{t.hi}</span>
                      <h3>{t.en}</h3>
                      <p>{t.note}</p>
                    </div>

                    <span className="tool-arrow">→</span>
                  </button>
                ))}
              </div>
            </section>

            <section className="how-section">
              <div className="section-title center-title">
                <span className="eyebrow">HOW IT WORKS</span>
                <h2>From classroom speech to understanding</h2>
              </div>

              <div className="steps">
                <div className="step">
                  <div>01</div>
                  <h3>Speak or Type</h3>
                  <p>
                    शिक्षक हिंदी में बोलते या लिखते हैं।
                  </p>
                </div>

                <div className="step-line"></div>

                <div className="step">
                  <div>02</div>
                  <h3>Translate</h3>
                  <p>
                    Classroom Bridge creates the Punjabi version.
                  </p>
                </div>

                <div className="step-line"></div>

                <div className="step">
                  <div>03</div>
                  <h3>Listen & Learn</h3>
                  <p>
                    Students hear and practise the translation.
                  </p>
                </div>
              </div>
            </section>
          </>
        ) : (
          <>
            <nav className="tabs">
              <button
                className="back-home"
                onClick={() => setTab("home")}
              >
                ← Home
              </button>

              {TABS.map((t) => (
                <button
                  key={t.id}
                  className={t.id === tab ? "active" : ""}
                  onClick={() => setTab(t.id)}
                >
                  <span>{t.icon}</span>
                  {t.en}
                </button>
              ))}
            </nav>

            <Screen />
          </>
        )}
      </main>

      <footer>
        <div>
          <b>कक्षा सेतु • Classroom Bridge</b>
          <p>
            Making multilingual classrooms more accessible.
          </p>
        </div>

        <div className="footer-languages">
          हिंदी → ਪੰਜਾਬੀ
        </div>
      </footer>
    </div>
  );
}