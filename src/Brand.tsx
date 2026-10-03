import { useId } from "react";

export default function Brand({ onHome, light = false }: { onHome: () => void; light?: boolean }) {
  const gradientId = useId().replace(/:/g, "");

  return (
    <button className={`brand${light ? " brand-light" : ""}`} onClick={onHome} aria-label="Green Street home">
      <svg className="brand-mark" viewBox="0 0 76 90" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="12" y1="10" x2="64" y2="82" gradientUnits="userSpaceOnUse">
            <stop stopColor="#559641" />
            <stop offset="1" stopColor="#123f35" />
          </linearGradient>
        </defs>
        <path fill={`url(#${gradientId})`} d="M10 41C8 23 20 11 40 8 50 7 59 5 66 2c1 19-4 32-17 41-8 6-18 9-27 6l34-31L10 41Z" />
        <path fill="#123f35" d="M57 40v42c0 5-3 8-8 8H9v-10l12-6v16h8V69l9-5v26h8V58l-25-10 36-8Z" />
      </svg>
      <span className="brand-wordmark"><span>Green</span><span>Street</span></span>
    </button>
  );
}
