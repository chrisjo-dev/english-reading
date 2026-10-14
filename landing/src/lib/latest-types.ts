// english-reading 의 tools/publish.py rebuild_root() 가 쓰는 latest.json 과 같은 모양.
// chips, answer, words, words_total 은 나중에 추가한 값이라 예전 latest.json 에는 없을 수 있다.
export type LangInfo = {
  count: number;
  latest: string;
  topic: string;
  sentences: string[];
  chips?: string[];
  answer?: string;
  words?: [string, string][];
};

export type LatestData = {
  date: string;
  words_total?: number;
  langs: Record<string, LangInfo>;
  recent: { lang: string; day: string; topic: string }[];
};
