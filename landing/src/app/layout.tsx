import type { Metadata } from "next";
import { FAQ } from "@/lib/faq";
import { loadLatest } from "@/lib/reading";
import "./globals.css";

const SITE = "https://read.wspace.ai.kr";
const TITLE = "독해한입 | 매일 영어, 일본어, 독일어 독해 연습 (무료 뉴스레터)";
const DESCRIPTION =
  "매일 아침 무료로 받는 외국어 읽기 뉴스레터. 영어 B1~B2, 일본어 N3(기초 N4~N5), 독일어 B1~B2 지문을 문장별 음성, 주요 단어, 모범 해석과 함께.";
const latest = loadLatest();
const OG_IMAGE = latest.langs.en?.latest ? `${SITE}/en/${latest.langs.en.latest}/thumb.png` : `${SITE}/en/thumb.png`;

// 사이트(WebSite)와 자주 묻는 질문(FAQPage) 구조화 데이터. 상위 사이트 www.wspace.ai.kr 의 일부로 묶는다.
const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE}/#website`,
      name: "독해한입: 매일 외국어 읽기",
      alternateName: "매일 외국어 읽기",
      url: `${SITE}/`,
      inLanguage: ["ko-KR", "en", "ja", "de"],
      description: DESCRIPTION,
      isPartOf: { "@id": "https://www.wspace.ai.kr/#website" },
      publisher: { "@id": "https://www.wspace.ai.kr/#person" },
    },
    {
      "@type": "Organization",
      "@id": `${SITE}/#organization`,
      name: "독해한입",
      alternateName: "매일 외국어 읽기",
      url: `${SITE}/`,
      logo: `${SITE}/assets/brand/icon-512.png`,
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
  alternates: { canonical: `${SITE}/` },
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
