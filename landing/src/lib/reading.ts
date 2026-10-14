import fs from "node:fs";
import path from "node:path";
import type { LatestData } from "./latest-types";

// 빌드 때 english-reading 의 content JSON 을 읽어 첫 화면 데이터를 만든다(publish.py rebuild_root 와 같은 규칙).
const ROOT = process.env.READING_ROOT ?? path.resolve(process.cwd(), "..");
const LANGS = ["en", "ja"];

function readJson(file: string) {
  return JSON.parse(fs.readFileSync(file, "utf-8"));
}

export function loadLatest(): LatestData {
  const data: LatestData = { date: "", langs: {}, recent: [] };
  const recent: LatestData["recent"] = [];
  for (const lang of LANGS) {
    const dir = path.join(ROOT, "content", lang);
    if (!fs.existsSync(dir)) continue;
    // 사이트에 실제로 올라간 날짜(<언어>/<날짜>/index.html)만 센다.
    const days = fs
      .readdirSync(dir)
      .map((f) => f.match(/^(\d{4}-\d{2}-\d{2})\.json$/)?.[1])
      .filter((d): d is string => !!d && fs.existsSync(path.join(ROOT, lang, d, "index.html")))
      .sort()
      .reverse();
    if (!days.length) continue;
    const today = readJson(path.join(dir, `${days[0]}.json`));
    data.langs[lang] = {
      count: days.length,
      latest: days[0],
      topic: today.topic,
      sentences: (today.sentences ?? []).slice(0, 3).map((s: { en: string }) => s.en),
    };
    if (days[0] > data.date) data.date = days[0];
    for (const day of days.slice(0, 6)) {
      recent.push({ lang, day, topic: readJson(path.join(dir, `${day}.json`)).topic });
    }
  }
  data.recent = recent
    .sort((a, b) => (a.day === b.day ? LANGS.indexOf(a.lang) - LANGS.indexOf(b.lang) : a.day < b.day ? 1 : -1))
    .slice(0, 6);
  return data;
}
