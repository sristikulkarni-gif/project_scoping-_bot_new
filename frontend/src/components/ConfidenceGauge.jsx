/**
 * ConfidenceGauge — SVG arc gauge that displays AI confidence score (0-100)
 * Colors: 0-39 = red, 40-74 = amber, 75-100 = emerald
 */
export default function ConfidenceGauge({ score, reasons = [] }) {
    if (score === undefined || score === null) return null;

    // Arc geometry
    const radius = 52;
    const cx = 64;
    const cy = 64;
    const startAngle = -210; // degrees from 3-o'clock
    const totalArc = 240;   // total sweep degrees
    const circumference = Math.PI * 2 * radius;
    const arcLen = (totalArc / 360) * circumference;
    const filledLen = (Math.max(0, Math.min(100, score)) / 100) * arcLen;

    // Convert angle to radians for SVG path
    const toRad = (deg) => (deg * Math.PI) / 180;
    const polarToCart = (angle, r) => ({
        x: cx + r * Math.cos(toRad(angle)),
        y: cy + r * Math.sin(toRad(angle)),
    });

    const start = polarToCart(startAngle, radius);
    const end = polarToCart(startAngle + totalArc, radius);
    const trackPath = `
    M ${start.x} ${start.y}
    A ${radius} ${radius} 0 1 1 ${end.x} ${end.y}
  `;

    // Color bands
    const color = score >= 75 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444";
    const glowColor = score >= 75 ? "rgba(16,185,129,0.35)" : score >= 40 ? "rgba(245,158,11,0.35)" : "rgba(239,68,68,0.35)";
    const label = score >= 75 ? "High Confidence" : score >= 40 ? "Moderate Confidence" : "Low Confidence";
    const sublabel = score >= 75 ? "Scope is reliable" : score >= 40 ? "PM Review Recommended" : "Senior Review Required";

    return (
        <div
            className="rounded-2xl p-5 mt-4"
            style={{
                background: "#131929",
                border: `1px solid rgba(255,255,255,0.07)`,
            }}
        >
            <div className="flex flex-col sm:flex-row items-center gap-6">
                {/* Arc Gauge SVG */}
                <div className="relative shrink-0 flex items-center justify-center">
                    <svg width="128" height="100" viewBox="0 0 128 100" className="overflow-visible">
                        <defs>
                            <filter id="gaugeglow">
                                <feGaussianBlur stdDeviation="2.5" result="blur" />
                                <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                        </defs>
                        {/* Track */}
                        <path
                            d={trackPath}
                            fill="none"
                            stroke="rgba(255,255,255,0.07)"
                            strokeWidth="10"
                            strokeLinecap="round"
                        />
                        {/* Filled arc */}
                        <path
                            d={trackPath}
                            fill="none"
                            stroke={color}
                            strokeWidth="10"
                            strokeLinecap="round"
                            strokeDasharray={`${filledLen} ${circumference}`}
                            strokeDashoffset={0}
                            filter="url(#gaugeglow)"
                            style={{ transition: "stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1)" }}
                        />
                    </svg>
                    {/* Center text */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ marginTop: "8px" }}>
                        <span className="text-3xl font-extrabold text-white leading-none">{score}</span>
                        <span className="text-xs text-slate-500 font-semibold">/100</span>
                    </div>
                </div>

                {/* Label + Reasons */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-base font-bold text-white">{label}</span>
                        <span
                            className="text-xs font-semibold px-2 py-0.5 rounded-full"
                            style={{ background: `${color}22`, color: color, border: `1px solid ${color}55` }}
                        >
                            AI Score
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-3">{sublabel}</p>
                    {reasons.length > 0 && (
                        <ul className="space-y-1.5">
                            {reasons.map((r, i) => (
                                <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
                                    <span style={{ color }} className="mt-0.5 shrink-0">•</span>
                                    {r}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
}
