import type { Metadata } from "next";
import { loadLatest } from "@/lib/reading";
import "./globals.css";

const SITE = "https://read.wspace.ai.kr";
const TITLE = "매일 외국어 읽기 | 매일 영어, 일본어 독해 연습 (무료 뉴스레터)";
const DESCRIPTION = "매일 아침 새로 올라오는 외국어 읽기. 문장별 음성, 주요 단어, 모범 해석.";
const latest = loadLatest();
const OG_IMAGE = latest.langs.en?.latest ? `${SITE}/en/${latest.langs.en.latest}/thumb.png` : `${SITE}/en/thumb.png`;

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: `${SITE}/` },
  openGraph: {
    type: "website",
    siteName: "매일 외국어 읽기",
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
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css" />
        <script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2339195232447097"
          crossOrigin="anonymous"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
