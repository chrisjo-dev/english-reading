import Header from "@/components/ref/Header";
import Opening from "@/components/ref/Opening";
import Prologue from "@/components/ref/Prologue";
import Chapter, { ArchiveHead } from "@/components/ref/Chapter";
import Footer from "@/components/ref/Footer";
import { LatestProvider } from "@/components/ref/latest";
import { TodayDate, TodayLeft, TodayRight, TodayStatement } from "@/components/ref/Live";
import { loadLatest } from "@/lib/reading";

const SUBSCRIBE = "https://buttondown.com/api/emails/embed-subscribe/english-reading";

// 문구 출처: english-reading tools/template.html 의 지문 도구 안내와 STEP 4 안내.
const STEPS = [
  {
    title: "읽고 듣기",
    desc: "지문을 읽고 전체 듣기로 들어 보세요. 문장 번호를 누르면 그 문장만 들을 수 있어요.",
  },
  {
    title: "번역 써 보기",
    desc: "모르는 단어가 나와도 문장을 버리지 말고, 아는 부분만이라도 지문 아래 '내 해석' 칸에 적어 보세요.",
  },
  {
    title: "AI 피드백 받기",
    desc: "다 쓰면 'AI 피드백 요청문 복사'를 눌러 평소 쓰는 AI 채팅(ChatGPT, Claude 등)에 붙여넣으세요. 어디를 잘 읽었고 어디를 놓쳤는지 문장별로 알려 줘요.",
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
  { lang: "en", label: "영어 지문 받기", level: "EN B1~B2" },
  { lang: "ja", label: "일본어 지문 받기", level: "JA N4~N5" },
];

export default function Home() {
  const data = loadLatest();
  return (
    <LatestProvider initial={data}>
      <Header />
      <main>
        <Opening />
        <Prologue />

        <section className="glance" aria-labelledby="glance-title">
          <div className="ch-meta">
            <span id="glance-title">서비스 한눈에 보기</span>
            <span>EN, JA</span>
          </div>
          <p className="glance-text">{GLANCE}</p>
        </section>

        <Chapter
          id="languages"
          meta={["01 / 04  오늘의 지문", <TodayDate key="d" />]}
          index="01 — 오늘의 지문"
          statement={<TodayStatement />}
          left={<TodayLeft />}
        >
          <TodayRight />
        </Chapter>

        <Chapter id="how" meta={["02 / 04  이용 방법", "세 단계"]} index="02 — 이용 방법" statement="세 단계면 충분해요.">
          <ArchiveHead left="읽고, 쓰고, 묻기" right="STEP 01 — 03" />
          {STEPS.map((s, i) => (
            <div key={s.title} className="ch-step">
              <span className="ch-row-k">0{i + 1}</span>
              <div>
                <div className="ch-step-t">{s.title}</div>
                <p className="ch-step-d">{s.desc}</p>
              </div>
            </div>
          ))}
        </Chapter>

        <Chapter
          id="subscribe"
          dark
          meta={["03 / 04  무료 구독", "매일 아침"]}
          index="03 — 무료 구독"
          statement="매일 아침 메일로 받아 보세요."
        >
          <ArchiveHead left="구독" right="언어 하나를 고르세요" />
          {FORMS.map((f) => (
            <form key={f.lang} className="sub-form" action={SUBSCRIBE} method="post" target="_blank">
              <label className="sub-label" htmlFor={`email-${f.lang}`}>
                {f.label} <span>{f.level}</span>
              </label>
              <input type="hidden" name="metadata__lang" value={f.lang} />
              <input
                id={`email-${f.lang}`}
                className="sub-input"
                type="email"
                name="email"
                required
                placeholder="이메일 주소"
                autoComplete="email"
              />
              <button className="sub-btn" type="submit">
                구독하기
              </button>
            </form>
          ))}
          <p className="sub-note">
            하나의 이메일로는 한 언어만 구독할 수 있어요. 영어와 일본어를 모두 받으시려면 서로 다른 이메일로 각각 구독해
            주세요.
          </p>
        </Chapter>

        <Chapter
          id="faq"
          meta={["04 / 04  자주 묻는 질문", `${FAQ.length}개 질문`]}
          index="04 — 자주 묻는 질문"
          statement="궁금한 점을 모았어요."
        >
          <ArchiveHead left="질문" right="눌러서 펼치기" />
          {FAQ.map((f, i) => (
            <details key={f.q} className="faq">
              <summary>
                <span className="ch-row-k">Q{i + 1}</span>
                <span className="ch-row-t">{f.q}</span>
                <span className="faq-plus" aria-hidden="true">
                  +
                </span>
              </summary>
              <p>{f.a}</p>
            </details>
          ))}
        </Chapter>
      </main>
      <Footer />
    </LatestProvider>
  );
}
