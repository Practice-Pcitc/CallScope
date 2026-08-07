import {
  useCallback,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode
} from "react";

interface ThreeColumnLayoutProps {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}

const LEFT_DEFAULT = 310;
const RIGHT_DEFAULT = 460;
const LEFT_KEY = "callscope:left-panel-width";
const RIGHT_KEY = "callscope:right-panel-width";

function storedWidth(key: string, fallback: number): number {
  const value = Number(window.localStorage.getItem(key));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function ThreeColumnLayout({
  left,
  center,
  right
}: ThreeColumnLayoutProps) {
  const layoutRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(() =>
    storedWidth(LEFT_KEY, LEFT_DEFAULT)
  );
  const [rightWidth, setRightWidth] = useState(() =>
    storedWidth(RIGHT_KEY, RIGHT_DEFAULT)
  );

  const startResize = useCallback(
    (side: "left" | "right", event: ReactPointerEvent) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = side === "left" ? leftWidth : rightWidth;
      document.body.classList.add("panel-resizing");

      const move = (moveEvent: PointerEvent) => {
        const containerWidth = layoutRef.current?.clientWidth ?? window.innerWidth;
        const delta = moveEvent.clientX - startX;
        const available =
          containerWidth -
          (side === "left" ? rightWidth : leftWidth) -
          430;
        const minimum = side === "left" ? 240 : 340;
        const maximum = Math.max(
          minimum,
          Math.min(side === "left" ? 520 : 720, available)
        );
        const next = Math.min(
          Math.max(
            side === "left" ? startWidth + delta : startWidth - delta,
            minimum
          ),
          maximum
        );
        if (side === "left") {
          setLeftWidth(next);
          window.localStorage.setItem(LEFT_KEY, String(Math.round(next)));
        } else {
          setRightWidth(next);
          window.localStorage.setItem(RIGHT_KEY, String(Math.round(next)));
        }
      };

      const finish = () => {
        document.body.classList.remove("panel-resizing");
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", finish);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", finish, { once: true });
    },
    [leftWidth, rightWidth]
  );

  const resetWidth = (side: "left" | "right") => {
    if (side === "left") {
      setLeftWidth(LEFT_DEFAULT);
      window.localStorage.setItem(LEFT_KEY, String(LEFT_DEFAULT));
    } else {
      setRightWidth(RIGHT_DEFAULT);
      window.localStorage.setItem(RIGHT_KEY, String(RIGHT_DEFAULT));
    }
  };

  return (
    <div
      ref={layoutRef}
      className="three-column-layout"
      style={{
        gridTemplateColumns: `${leftWidth}px 6px minmax(420px, 1fr) 6px ${rightWidth}px`
      }}
    >
      <aside className="panel left-panel">{left}</aside>
      <div
        className="panel-resizer"
        role="separator"
        aria-label="调节接口列表宽度"
        aria-orientation="vertical"
        onPointerDown={(event) => startResize("left", event)}
        onDoubleClick={() => resetWidth("left")}
      />
      <section className="graph-panel">{center}</section>
      <div
        className="panel-resizer"
        role="separator"
        aria-label="调节分析面板宽度"
        aria-orientation="vertical"
        onPointerDown={(event) => startResize("right", event)}
        onDoubleClick={() => resetWidth("right")}
      />
      <aside className="panel right-panel">{right}</aside>
    </div>
  );
}
