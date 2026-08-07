import type { ReactNode } from "react";

interface ThreeColumnLayoutProps {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}

export function ThreeColumnLayout({
  left,
  center,
  right
}: ThreeColumnLayoutProps) {
  return (
    <div className="three-column-layout">
      <aside className="panel left-panel">{left}</aside>
      <section className="graph-panel">{center}</section>
      <aside className="panel right-panel">{right}</aside>
    </div>
  );
}

