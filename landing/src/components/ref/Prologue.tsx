"use client";

import { useEffect, useRef, useState } from "react";

const LINES = ["First, we memorized words.", "Then we read sentences.", "Now we read every day."];

export default function Prologue() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const totalHeight = el.offsetHeight - window.innerHeight;
      const scrolled = -rect.top;
      const progress = Math.max(0, Math.min(1, scrolled / totalHeight));
      const index = Math.floor(progress * LINES.length);
      setActiveIndex(Math.min(index, LINES.length - 1));
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div ref={containerRef} className="pro">
      {/* Sticky scene */}
      <div className="pro-stage">
        {/* Left meta */}
        <div className="pro-meta">
          <div>읽기의 순서</div>
          <div>세 단계</div>
        </div>

        {/* Rolling lines: 스크립트가 없으면 모두 보인다(.js 일 때만 뒤 줄을 숨김) */}
        <div className="pro-lines">
          {LINES.map((line, i) => {
            const state =
              i < activeIndex ? "past" : i === activeIndex ? "current" : i === activeIndex + 1 ? "next" : "hidden";
            return (
              <div key={i} className="pro-line" data-state={state} lang="en">
                {line}
              </div>
            );
          })}
        </div>

        {/* Description under current line */}
        <div className="pro-desc">매일 아침 짧은 지문 하나. 듣고, 해석하고, AI에게 피드백을 받습니다.</div>

        {/* Bottom-right arrow */}
        <div className="pro-arrow" aria-hidden="true">
          &#8595;
        </div>
      </div>
    </div>
  );
}
