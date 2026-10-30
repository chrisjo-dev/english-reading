import Footer from "@/components/Footer";
import { CONFIRM_NOTE } from "@/components/forms";
import Hero from "@/components/Hero";
import Motion from "@/components/Motion";
import Nav from "@/components/Nav";
import SubFormsList from "@/components/SubFormsList";
import Week, { WeekMeta } from "@/components/Week";
import { LatestProvider } from "@/components/ref/latest";
import { FAQ } from "@/lib/faq";
import { loadLatest } from "@/lib/reading";

const STEPS = [
  {
    time: "07:00",
    title: "메일이 와요",
    desc: "매일 아침 7시 전후, 오늘의 지문이 메일로 와요. 영어(B1~B2), 일본어(N3, 기초 N4~N5), 독일어(B1~B2) 중 하나를 골라 받아요.",
  },
  {
    time: "07:01",
    title: "듣고, 써 봐요",
    desc: "문장마다 합성 음성이 붙어 있어요. 내 해석을 먼저 써 보고 모범 해석과 핵심 단어로 맞춰 봐요.",
  },
  {
    time: "07:05",
    title: "AI에게 물어요",
    desc: "'AI 피드백 요청문 복사'를 누르면 지문과 내 해석이 함께 복사돼요. ChatGPT나 Claude에 붙여 넣으면 돼요.",
  },
];

// 검색과 AI 답변에 인용되도록, 무엇을 누구에게 얼마나 자주 어떤 수준으로 주는지 한 문단에 담는다.
const GLANCE =
  "매일 외국어 읽기(read.wspace.ai.kr)는 매일 아침 CEFR B1~B2 영어 지문, JLPT N3(기초 N4~N5) 일본어 지문, CEFR B1~B2 독일어 지문을 이메일로 보내 주는 무료 뉴스레터예요. 지문은 5문장 안팎으로 약 3분이면 읽을 수 있어요. 문장별 음성, 주요 단어 풀이, 모범 해석, AI 피드백을 모두 무료로 이용할 수 있어요.";

const delay = (i: number) => ({ transitionDelay: `${i * 60}ms` });

export default function Home() {
  const data = loadLatest();
  return (
    <LatestProvider initial={data}>
      <Nav />
      <main>
        <Hero />

        <section className="sec" id="how" data-reveal aria-labelledby="how-h">
          <div className="wrap">
            <div className="sec-head">
              <span className="mono">02 / 이용 방법</span>
              <h2 id="how-h">세 단계면 오늘 몫은 끝나요.</h2>
            </div>
            <ol className="steps">
              {STEPS.map((s, i) => (
                <li key={s.title} className="rv" style={delay(i)}>
                  <span className="mono st-t">{s.time}</span>
                  <h3>{s.title}</h3>
                  <p>{s.desc}</p>
                </li>
              ))}
            </ol>
            <p className="note mono rv" style={delay(3)}>
              일요일에는 그 주의 핵심 단어를 모은 주간 단어 복습 메일이 따로 와요.
            </p>
          </div>
        </section>

        <section className="sec" id="week" data-reveal aria-labelledby="week-h">
          <div className="wrap">
            <div className="sec-head">
              <span className="mono">03 / 이번 주 지문</span>
              <h2 id="week-h">이번 주에 나온 지문이에요.</h2>
              <span className="mono sec-meta">
                <WeekMeta />
              </span>
            </div>
            <Week />
            {/* 언어별 지난 지문 입구. 휴대폰은 상단 메뉴가 없어 여기가 목록으로 가는 길이다(이슈 #19) */}
            <nav className="week-all" id="past" aria-label="언어별 지난 지문">
              <a href="/en/archive/">영어 지난 지문 전체 보기<span aria-hidden="true">→</span></a>
              <a href="/ja/archive/">일본어 지난 지문 전체 보기<span aria-hidden="true">→</span></a>
              <a href="/de/archive/">독일어 지난 지문 전체 보기<span aria-hidden="true">→</span></a>
            </nav>
          </div>
        </section>

        <section className="sec" id="glance" data-reveal aria-labelledby="glance-h">
          <div className="wrap">
            <div className="sec-head">
              <h2 id="glance-h" className="mono">
                04 / 서비스 한눈에 보기
              </h2>
            </div>
            <p className="glance rv">{GLANCE}</p>
          </div>
        </section>

        <section className="sec" id="faq" data-reveal aria-labelledby="faq-h">
          <div className="wrap">
            <div className="sec-head">
              <span className="mono">05 / 자주 묻는 질문</span>
              <h2 id="faq-h">궁금한 점이 있나요?</h2>
              <span className="mono sec-meta">{FAQ.length}개 질문</span>
            </div>
            <div className="faq">
              {FAQ.map((f, i) => (
                <details key={f.q} className="rv" style={delay(i)}>
                  <summary>
                    <span className="mono q">Q{i + 1}</span>
                    <span className="qt">{f.q}</span>
                    <span className="plus" aria-hidden="true" />
                  </summary>
                  <p>{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="sec sub" id="subscribe" data-reveal aria-labelledby="sub-h">
          <div className="wrap">
            <div className="sec-head">
              <span className="mono">06 / 무료 구독</span>
              <h2 id="sub-h">매일 아침 메일로 받아 보세요.</h2>
            </div>
            <div className="sub-forms">
              <SubFormsList />
            </div>
            <p className="note mono rv" style={delay(3)}>
              하나의 이메일로는 한 언어만 구독할 수 있어요. 여러 언어를 받으시려면 서로 다른 이메일로 각각 구독해 주세요. 이미 구독 중이어도 같은 이메일로 다시 구독하면 수준과 언어가 바로 바뀌어요.
              <span className="confirm-note">{CONFIRM_NOTE}</span>
            </p>
          </div>
        </section>
      </main>
      <Footer />
      <Motion />
    </LatestProvider>
  );
}
