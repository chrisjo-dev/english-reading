import type { Metadata } from "next";
import { FAQ } from "@/lib/faq";
import { loadLatest } from "@/lib/reading";
import { MIGRATE_JS } from "@/lib/migrate";
import { ALT_NAMES, SAME_AS, SITE } from "@/lib/site";
import "./globals.css";
import "./gnb.css";

const TITLE = "독해한입 | 매일 영어, 일본어, 독일어 독해 연습 (무료 뉴스레터)";
const DESCRIPTION =
  "매일 아침 무료로 받는 외국어 읽기 뉴스레터. 영어 B1~B2, 일본어 N3(기초 N4~N5), 독일어 B1~B2 지문을 문장별 음성, 주요 단어, 모범 해석과 함께.";
const latest = loadLatest();
const OG_IMAGE = latest.langs.en?.latest ? `${SITE}/en/${latest.langs.en.latest}/thumb.png` : `${SITE}/en/thumb.png`;

// 사이트(WebSite), 운영 주체(Organization), 자주 묻는 질문(FAQPage) 구조화 데이터. 상위 사이트 www.wspace.ai.kr 의 일부로 묶는다.
// 지문 페이지(tools/publish.py reading_ld)도 같은 @id 로 #organization, #website 노드를 짧게 다시 정의한다(그 페이지 안에서도 풀리게).
// 전체 정의(설명, founder, FAQ)는 여기에 두고, 이름, 로고, sameAs 는 양쪽이 같게 둔다.
// alternateName(ALT_NAMES, lib/site): 붙여 쓰기, 순서를 바꾼 이름, 로마자로 찾는 사람도 같은 서비스로 이어지게 한다(화면 문구에는 넣지 않는다).
const PERSON = "https://www.wspace.ai.kr/#person";
const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE}/#website`,
      name: "독해한입: 매일 외국어 읽기",
      alternateName: ["독해한입", ...ALT_NAMES],
      url: `${SITE}/`,
      inLanguage: ["ko-KR", "en", "ja", "de"],
      description: DESCRIPTION,
      isPartOf: { "@id": "https://www.wspace.ai.kr/#website" },
      publisher: { "@id": `${SITE}/#organization` },
    },
    {
      "@type": "Organization",
      "@id": `${SITE}/#organization`,
      name: "독해한입",
      alternateName: ALT_NAMES,
      url: `${SITE}/`,
      description:
        "영어, 일본어, 독일어 독해 지문을 문장별 음성, 주요 단어, 모범 해석과 함께 매일 아침 무료로 올리고 메일로 보내는 1인 운영 서비스.",
      logo: { "@type": "ImageObject", url: `${SITE}/assets/brand/icon-512.png`, width: 512, height: 512 },
      founder: { "@id": PERSON },
      sameAs: SAME_AS,
    },
    // 운영자. 상위 사이트(www.wspace.ai.kr) 노드에 있는 이름, 주소, 프로필만 옮겨 이 페이지에서도 @id 가 풀리게 한다.
    {
      "@type": "Person",
      "@id": PERSON,
      name: "Chris Jo",
      url: "https://www.wspace.ai.kr/about/",
      sameAs: ["https://github.com/chrisjo-dev"],
    },
    {
      "@type": "FAQPage",
      "@id": `${SITE}/#faq`,
      mainEntity: FAQ.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    },
  ],
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: `${SITE}/`, types: { "application/rss+xml": `${SITE}/rss.xml` } },
  openGraph: {
    type: "website",
    siteName: "독해한입: 매일 외국어 읽기",
    locale: "ko_KR",
    title: TITLE,
    description: DESCRIPTION,
    url: `${SITE}/`,
    images: [{ url: OG_IMAGE, width: 1200, height: 630 }],
  },
  twitter: { card: "summary_large_image", title: TITLE, description: DESCRIPTION, images: [OG_IMAGE] },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        {/* 예전 주소에서 넘어온 학습 기록 받기(id="mig", 지문 페이지와 같은 스크립트) */}
        <script id="mig" dangerouslySetInnerHTML={{ __html: MIGRATE_JS }} />
        {/* 숨김 상태는 .js 일 때만 적용한다(스크립트 없이도 모든 내용이 보이게). */}
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
        <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD).replace(/<\//g, "<\\/") }}
        />
        <script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2339195232447097"
          crossOrigin="anonymous"
        />
        {/* Google Analytics 4 */}
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-43L9WRDB2N" />
        <script dangerouslySetInnerHTML={{ __html: "window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-43L9WRDB2N',{anonymize_ip:true});" }} />
        {/* Microsoft Clarity */}
        <script dangerouslySetInnerHTML={{ __html: "(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};t=l.createElement(r);t.async=1;t.src='https://www.clarity.ms/tag/'+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})(window,document,'clarity','script','yxuphaowch');" }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
