import type {BoardCell, BoardState, PlayerSymbol} from "../api/game.ts";

type Connect4BoardProps = {
    active?: boolean;
    statusLabel?: string;
    board?: BoardState;
    boardCaption?: string;
    canMove?: boolean;
    currentPlayerSymbol?: PlayerSymbol;
    playerSymbol?: PlayerSymbol | null;
    movePending?: boolean;
    onColumnSelect?: (column: number) => void;
};

const COLUMNS = 7;
const ROWS = 6;
const EMPTY_BOARD: BoardState = Array.from(
    {length: ROWS},
    () => Array.from({length: COLUMNS}, () => 0 as BoardCell),
);

function getCellClasses(value: BoardCell) {
    if (value === 1) {
        return "border-red-200/40 bg-red-500 shadow-[inset_0_10px_18px_rgba(254,202,202,0.45),0_5px_12px_rgba(127,29,29,0.55)]";
    }

    if (value === 2) {
        return "border-yellow-100/60 bg-yellow-300 shadow-[inset_0_10px_18px_rgba(254,249,195,0.55),0_5px_12px_rgba(113,63,18,0.45)]";
    }

    return "border-slate-950/10 bg-slate-950/80 shadow-[inset_0_10px_18px_rgba(15,23,42,0.95),0_4px_10px_rgba(15,23,42,0.35)]";
}

export default function Connect4Board({
    active = false,
    statusLabel,
    board = EMPTY_BOARD,
    boardCaption,
    canMove = false,
    currentPlayerSymbol,
    playerSymbol,
    movePending = false,
    onColumnSelect,
}: Connect4BoardProps) {
    const cells = Array.from({length: COLUMNS * ROWS}, (_, index) => {
        const row = Math.floor(index / COLUMNS);
        const column = index % COLUMNS;
        return {
            index,
            row,
            column,
            value: board[row]?.[column] ?? 0,
        };
    });
    const columns = Array.from({length: COLUMNS}, (_, column) => column);

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
                            {boardCaption ?? (active ? "Room is live. Waiting for the next confirmed move." : "Preview your private match before the room goes live.")}
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
                                key={cell.index}
                                className={`
                                    aspect-square rounded-full border ${getCellClasses(cell.value)}
                                    ${cell.value === currentPlayerSymbol ? "ring-2 ring-white/65" : active ? "ring-1 ring-cyan-100/10" : ""}
                                `}
                            >
                                <div className="h-full w-full rounded-full bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.28),rgba(255,255,255,0.04)_42%,transparent_62%)]" />
                            </div>
                        ))}
                    </div>
                    <div className="absolute inset-3 grid grid-cols-7 gap-2 sm:gap-3">
                        {columns.map((column) => {
                            const columnOpen = (board[0]?.[column] ?? 1) === 0;
                            const enabled = canMove && columnOpen && !movePending;

                            return (
                                <button
                                    key={column}
                                    type="button"
                                    disabled={!enabled}
                                    onClick={() => onColumnSelect?.(column)}
                                    className={`
                                        h-full rounded-[1rem] transition
                                        enabled:cursor-pointer enabled:hover:bg-white/10 enabled:focus-visible:outline-none enabled:focus-visible:ring-2 enabled:focus-visible:ring-white/70
                                        disabled:cursor-not-allowed
                                        ${playerSymbol === 1 ? "enabled:hover:ring-2 enabled:hover:ring-red-100/60" : ""}
                                        ${playerSymbol === 2 ? "enabled:hover:ring-2 enabled:hover:ring-yellow-100/70" : ""}
                                    `}
                                >
                                    <span className="sr-only">Drop piece in column {column + 1}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
