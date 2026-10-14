// english-reading 의 tools/publish.py rebuild_root() 가 쓰는 latest.json 과 같은 모양.
export type LangInfo = {
  count: number;
  latest: string;
  topic: string;
  sentences: string[];
};

export type LatestData = {
  date: string;
  langs: Record<string, LangInfo>;
  recent: { lang: string; day: string; topic: string }[];
};
