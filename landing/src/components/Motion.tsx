"use client";

import { useEffect } from "react";

// 첫 화면 움직임. transform 과 opacity 만 바꾼다. 움직임 줄이기 설정이면 아무것도 하지 않는다(CSS 가 최종 상태로 둔다).
export default function Motion() {
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const off: (() => void)[] = [];

    // 1. 스크롤 처음 60vh 동안 폰을 -6도에서 0도로 세우고, 옆 라벨 숫자도 함께 바꾼다.
    const phone = document.querySelector<HTMLElement>("[data-phone]");
    const deg = document.querySelector<HTMLElement>("[data-deg]");
    if (phone) {
      let queued = false;
      const draw = () => {
        queued = false;
        const p = Math.min(1, Math.max(0, scrollY / (innerHeight * 0.6)));
        const r = -6 * (1 - p);
        phone.style.transform = `rotate(${r.toFixed(2)}deg)`;
        if (deg) deg.textContent = `${r > -0.05 ? "0" : r.toFixed(1)}°`;
      };
      const onScroll = () => {
        if (!queued) {
          queued = true;
          requestAnimationFrame(draw);
        }
      };
      addEventListener("scroll", onScroll, { passive: true });
      addEventListener("resize", onScroll);
      draw();
      off.push(() => {
        removeEventListener("scroll", onScroll);
        removeEventListener("resize", onScroll);
      });
    }

    // 2. "매일 아침." 밑줄과 아래 섹션은 화면에 들어올 때 한 번만 나타난다.
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue;
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.12 },
    );
    document.querySelectorAll("[data-sweep], [data-reveal]").forEach((el) => io.observe(el));
    off.push(() => io.disconnect());

    return () => off.forEach((f) => f());
  }, []);
  return null;
}
