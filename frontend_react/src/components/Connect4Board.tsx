type Connect4BoardProps = {
    active?: boolean;
    statusLabel?: string;
};

const COLUMNS = 7;
const ROWS = 6;

export default function Connect4Board({active = false, statusLabel}: Connect4BoardProps) {
    const cells = Array.from({length: COLUMNS * ROWS}, (_, index) => index);

    return (
        <div className="relative mx-auto w-full max-w-2xl">
            <div className="absolute inset-x-6 -top-6 h-24 rounded-full bg-cyan-400/25 blur-3xl" />
            <div
                className={`
                    relative overflow-hidden rounded-[2rem] border border-white/10 p-4 shadow-2xl shadow-slate-950/40 backdrop-blur
                    ${active ? "bg-slate-900/85" : "bg-slate-900/70"}
                `}
            >
                <div className="mb-4 flex items-center justify-between gap-4">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-200/70">
                            Connect 4 Board
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                            {active ? "Room is live. The board is ready for the first move." : "Preview your private match before the room goes live."}
                        </p>
                    </div>
                    {statusLabel && (
                        <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-medium text-cyan-100">
                            {statusLabel}
                        </span>
                    )}
                </div>

                <div className="relative rounded-[1.75rem] bg-gradient-to-b from-sky-400 via-blue-500 to-blue-700 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.3)]">
                    <div className="pointer-events-none absolute inset-x-4 top-0 h-10 rounded-b-[2rem] bg-white/15 blur-xl" />
                    <div className="grid grid-cols-7 gap-2 sm:gap-3">
                        {cells.map((cell) => (
                            <div
                                key={cell}
                                className={`
                                    aspect-square rounded-full border border-slate-950/10 bg-slate-950/80 shadow-[inset_0_10px_18px_rgba(15,23,42,0.95),0_4px_10px_rgba(15,23,42,0.35)]
                                    ${active ? "ring-1 ring-cyan-100/10" : ""}
                                `}
                            >
                                <div className="h-full w-full rounded-full bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.14),rgba(255,255,255,0.02)_42%,transparent_62%)]" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
