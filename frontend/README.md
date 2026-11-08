# Classroom Bridge – Frontend (React + Vite)

Web app for the SIH26042 project: Hindi to Punjabi translation, live voice, worksheets, flashcards.

## Run
1. Install Node.js LTS from https://nodejs.org (once).
2. Start the backend first (see the backend README) on http://127.0.0.1:8000.
3. In this folder:
```
npm install
npm run dev
```
4. Open http://localhost:5173 in **Chrome or Edge**.

If your backend runs somewhere else, copy `.env.example` to `.env` and change `VITE_API_URL`.

## Notes
- Live Class uses the browser's Hindi speech recognition (`hi-IN`). It needs internet and microphone permission; it works on localhost.
- Worksheets open the print dialog: choose "Save as PDF".
- Build for hosting: `npm run build` (output in `dist/`).
