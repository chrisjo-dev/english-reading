import { Markup } from "./ref/latest";
import { dotDate, weekday } from "./util";

// 목업의 파형 높이를 그대로 쓴다. 앞 17칸은 재생된 부분(파랑).
const WAVE = [8, 12, 9, 14, 19, 10, 7, 6, 5, 12, 11, 9, 14, 11, 16, 20, 13, 5, 5, 5, 14, 15, 4, 9, 6, 10, 17, 11, 8, 8, 9, 18, 20, 11, 6, 8, 5, 14, 10, 7];
const PLAYED = 17;

type Props = { date: string; topic: string; chips: string[]; sentences: string[]; draft: string };

// 오늘의 영어 지문 페이지를 줄여 그린 폰. 화면 낭독기에는 감싼 링크의 이름으로 전달하고 안쪽은 숨긴다.
export default function Phone({ date, topic, chips, sentences, draft }: Props) {
  const [s1, s2, s3, s4] = sentences;
  return (
    <div className="phone" aria-hidden="true">
      <div className="ph-screen">
        <div className="ph-status">
          <span>07:03</span>
          <span className="ph-island" />
          <svg width="38" height="11" viewBox="0 0 38 11">
            <rect x="0" y="6" width="3" height="5" rx="1" fill="currentColor" />
            <rect x="5" y="4" width="3" height="7" rx="1" fill="currentColor" />
            <rect x="10" y="2" width="3" height="9" rx="1" fill="currentColor" />
            <rect x="15" y="0" width="3" height="11" rx="1" fill="currentColor" />
            <rect x="22" y="1" width="14" height="9" rx="2.5" fill="none" stroke="currentColor" />
            <rect x="24" y="3" width="9" height="5" rx="1" fill="currentColor" />
          </svg>
        </div>
        <div className="ph-app">
          <span className="ph-brand">
            <i />
            매일 외국어 읽기
          </span>
          <span className="ph-pill">EN</span>
        </div>
        <div className="ph-date mono">
          {dotDate(date)} {weekday(date)} / 오늘의 지문
        </div>
        <div className="ph-topic">{topic}</div>
        <div className="ph-chips">
          {chips.map((c) => (
            <span key={c}>{c}</span>
          ))}
        </div>
        <ol className="ph-list" lang="en">
          {s1 && (
            <li className="on">
              <span className="n mono">01</span>
              <div>
                <p>
                  <Markup text={s1} />
                </p>
                <div className="ph-play">
                  <span className="pb">
                    <svg viewBox="0 0 20 20">
                      <rect x="6" y="5" width="3" height="10" fill="currentColor" />
                      <rect x="11" y="5" width="3" height="10" fill="currentColor" />
                    </svg>
                  </span>
                  <svg className="wave" viewBox="0 0 160 20" preserveAspectRatio="none">
                    {WAVE.map((h, i) => (
                      <rect
                        key={i}
                        x={i * 4}
                        y={(20 - h) / 2}
                        width="2"
                        height={h}
                        rx="1"
                        className={i < PLAYED ? "on" : undefined}
                        style={{ animationDelay: `${(i % 9) * -0.18}s` }}
                      />
                    ))}
                  </svg>
                </div>
              </div>
            </li>
          )}
          {s2 && (
            <li>
              <span className="n mono">02</span>
              <p>
                <Markup text={s2} />
              </p>
            </li>
          )}
          {s3 && (
            <li>
              <span className="n mono">03</span>
              <p className="clamp">
                <Markup text={s3} />
              </p>
            </li>
          )}
        </ol>
        <div className="ph-input">
          <span className="mono">내 해석</span>
          <p>
            {draft}
            <span className="caret" />
          </p>
        </div>
        <div className="ph-cta">
          <svg width="14" height="14" viewBox="0 0 14 14">
            <rect x="4.5" y="4.5" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
            <path d="M2 9.5V3a1.5 1.5 0 0 1 1.5-1.5H9" fill="none" stroke="currentColor" strokeWidth="1.3" />
          </svg>
          AI 피드백 요청문 복사
        </div>
        {s4 && (
          <ol className="ph-list rest" lang="en">
            <li>
              <span className="n mono">04</span>
              <p className="clamp">
                <Markup text={s4} />
              </p>
            </li>
          </ol>
        )}
      </div>
    </div>
  );
}
