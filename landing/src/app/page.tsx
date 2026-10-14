import Footer from "@/components/Footer";
import { SUBSCRIBE } from "@/components/forms";
import Hero from "@/components/Hero";
import Motion from "@/components/Motion";
import Nav from "@/components/Nav";
import Week, { WeekMeta } from "@/components/Week";
import { LatestProvider } from "@/components/ref/latest";
import { loadLatest } from "@/lib/reading";

const STEPS = [
  {
    time: "07:00",
    title: "메일이 와요",
    desc: "매일 아침 7시 전후, 오늘의 지문이 메일로 와요. 영어(B1~B2)나 일본어(N4~N5) 중 하나를 골라 받아요.",
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
  "매일 외국어 읽기(read.wspace.ai.kr)는 매일 아침 CEFR B1~B2 영어 지문 또는 JLPT N4~N5 일본어 지문을 이메일로 보내 주는 무료 뉴스레터예요. 지문은 5문장 안팎으로 약 3분이면 읽을 수 있어요. 문장별 음성, 주요 단어 풀이, 모범 해석, AI 피드백을 모두 무료로 이용할 수 있어요.";

const FAQ = [
  {
    q: "이 서비스는 무료인가요?",
    a: "완전 무료예요. 회원가입도, 카드 등록도 필요 없어요. CEFR B1~B2 영어 지문, JLPT N4~N5 일본어 지문, 문장별 음성, 주요 단어, 모범 해석, AI 피드백 기능을 모두 무료로 이용할 수 있어요.",
  },
  {
    q: "어떤 수준의 학습자에게 맞나요?",
    a: "영어는 CEFR B1~B2 수준으로 중급 학습자에게 적합해요. 일본어는 JLPT N4~N5 수준으로 초중급 학습자에게 맞아요. 기초 문법은 알지만 독해 연습과 실전 읽기가 필요한 분께 맞아요.",
  },
  {
    q: "지문은 매일 어떤 내용인가요?",
    a: "영어는 최근 소식을, 일본어는 일본의 생활과 문화를 바탕으로 새로 쓴 5문장 안팎의 짧은 지문이에요. 약 3분이면 읽을 수 있어요. 기사를 바탕으로 한 글은 출처를 밝혀요.",
  },
  {
    q: "이메일 뉴스레터는 언제 오나요?",
    a: "새 지문이 올라오면 매일 아침 7시 전후에 이메일로 보내 드려요. 매주 일요일에는 그 주의 주요 단어를 복습하는 주간 단어 복습 메일도 따로 보내요.",
  },
  {
    q: "AI 피드백은 어떻게 받나요?",
    a: "지문 페이지에서 내 번역을 써 본 뒤 'AI 피드백 요청문 복사' 버튼을 누르면, 지문과 번역이 함께 클립보드에 복사돼요. ChatGPT나 Claude 같은 AI에 붙여 넣으면 틀린 부분과 더 자연스러운 표현을 알려 줘요.",
  },
  {
    q: "하나의 이메일로 두 언어를 모두 받을 수 있나요?",
    a: "지금은 한 이메일 주소로 한 언어만 구독할 수 있어요. 영어와 일본어를 모두 받으시려면 서로 다른 이메일 주소로 각각 구독해 주세요.",
  },
];

const FORMS = [
  { lang: "en", label: "영어 지문 받기", level: "EN B1~B2", desc: "최근 소식을 바탕으로 쓴 영어 지문" },
  { lang: "ja", label: "일본어 지문 받기", level: "JA N4~N5", desc: "일본의 생활과 문화를 다룬 일본어 지문" },
];

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
              {FORMS.map((f, i) => (
                <form key={f.lang} className="sub-form rv" style={delay(i)} action={SUBSCRIBE} method="post" target="_blank" rel="noopener noreferrer">
                  <div className="mono k">
                    <span>{f.level}</span>
                    <span>{f.desc}</span>
                  </div>
                  <label className="sub-label" htmlFor={`email-${f.lang}`}>
                    {f.label}
                  </label>
                  <input type="hidden" name="metadata__lang" value={f.lang} />
                  <div className="row">
                    <input id={`email-${f.lang}`} type="email" name="email" required placeholder="이메일 주소" autoComplete="email" />
                    <button type="submit">구독하기</button>
                  </div>
                </form>
              ))}
            </div>
            <p className="note mono rv" style={delay(2)}>
              하나의 이메일로는 한 언어만 구독할 수 있어요. 영어와 일본어를 모두 받으시려면 서로 다른 이메일로 각각 구독해
              주세요.
            </p>
          </div>
        </section>
      </main>
      <Footer />
      <Motion />
    </LatestProvider>
  );
}
