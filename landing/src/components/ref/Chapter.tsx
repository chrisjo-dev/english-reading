type ChapterProps = {
  id: string;
  meta: [React.ReactNode, React.ReactNode];
  index: string;
  statement: React.ReactNode;
  left?: React.ReactNode;
  children: React.ReactNode;
  dark?: boolean;
};

// 장 하나: 위 메타 줄, 왼쪽(번호, 한 줄 요약, 링크), 오른쪽(본문과 목록).
export default function Chapter({ id, meta, index, statement, left, children, dark }: ChapterProps) {
  return (
    <section id={id} className={dark ? "ch is-dark" : "ch"}>
      {/* Meta row */}
      <div className="ch-meta">
        <span>{meta[0]}</span>
        <span>{meta[1]}</span>
      </div>

      {/* Two-column layout */}
      <div className="ch-grid">
        <div className="ch-left">
          <div className="ch-index">{index}</div>
          <h2 className="ch-statement">{statement}</h2>
          {left}
        </div>
        <div className="ch-right">{children}</div>
      </div>
    </section>
  );
}

export function ArchiveHead({ left, right }: { left: string; right: string }) {
  return (
    <div className="ch-arch-head">
      <span>{left}</span>
      <span>{right}</span>
    </div>
  );
}
