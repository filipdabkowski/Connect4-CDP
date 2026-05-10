
import React, {useEffect, useRef, useState} from "react";
import Connect4Board from "../components/Connect4Board.tsx";
import FormInput from "../components/FormInput.tsx";
import MainButton from "../components/MainButton.tsx";
import {useAuth} from "../auth/useAuth.ts";
import {createRoom, joinRoom, leaveRoom, type PlayerSymbol, type RoomErrorResponse, type RoomState} from "../api/game.ts";
import {api} from "../api/client.ts";
import axios from "axios";

type RoomPhase = "idle" | "creating" | "connecting" | "connected" | "error";

function normalizeRoomCode(value: string) {
    return value.trim().replace(/\s+/g, "").toUpperCase();
}

function buildGameSocketUrl(roomCode: string) {
    const apiBaseUrl = api.defaults.baseURL ?? "http://localhost:8000/api/";
    const backendUrl = new URL(apiBaseUrl);
    const protocol = backendUrl.protocol === "https:" ? "wss:" : "ws:";
    const token = localStorage.getItem("access_token");
    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : "";

    return `${protocol}//${backendUrl.host}/ws/game/${roomCode}/${tokenQuery}`;
}

function getApiErrorMessage(error: unknown, fallback: string) {
    if (axios.isAxiosError<{message?: string}>(error)) {
        return error.response?.data?.message ?? fallback;
    }

    return fallback;
}

function isRoomState(payload: unknown): payload is RoomState {
    if (!payload || typeof payload !== "object") return false;

    const candidate = payload as Partial<RoomState>;
    return typeof candidate.roomCode === "string" && typeof candidate.status === "string";
}

function isRoomError(payload: unknown): payload is RoomErrorResponse {
    if (!payload || typeof payload !== "object") return false;

    const candidate = payload as {type?: unknown; message?: unknown};
    return candidate.type === "room_error" && typeof candidate.message === "string";
}

function buildRoomHeading(roomState: RoomState | null, fallbackUsername?: string) {
    if (!roomState) return "Private Connect 4";

    const player1 = roomState.player1 ?? "Waiting...";
    const player2 = roomState.player2 ?? "Waiting...";

    if (!roomState.player1 && !roomState.player2 && fallbackUsername) {
        return `${fallbackUsername} vs Waiting...`;
    }

    return `${player1} vs ${player2}`;
}

function getCurrentUserSymbol(roomState: RoomState | null, username?: string): PlayerSymbol | null {
    if (!roomState || !username) return null;

    if (roomState.player1 === username) return 1;
    if (roomState.player2 === username) return 2;
    return null;
}

function getTurnMessage(roomState: RoomState, username?: string) {
    if (roomState.status !== "ready") {
        return "Waiting for another player.";
    }

    if (roomState.currentPlayer.username === username) {
        return "Your move.";
    }

    return `${roomState.currentPlayer.username ?? "Opponent"}'s move.`;
}

function getRoomStatusMessage(roomState: RoomState, username?: string) {
    const turnMessage = getTurnMessage(roomState, username);

    if (roomState.type === "player_move" && roomState.lastMove) {
        const playerName = roomState.lastMove.player.username ?? "A player";
        return `${playerName} played column ${roomState.lastMove.column + 1}. ${turnMessage}`;
    }

    return turnMessage;
}

export default function HomePage() {
    const {user, logout} = useAuth();
    const socketRef = useRef<WebSocket | null>(null);
    const manualDisconnectRef = useRef(false);

    const [roomInput, setRoomInput] = useState("");
    const [activeRoomCode, setActiveRoomCode] = useState<string | null>(null);
    const [roomState, setRoomState] = useState<RoomState | null>(null);
    const [roomPhase, setRoomPhase] = useState<RoomPhase>("idle");
    const [roomError, setRoomError] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState("No room joined yet.");
    const [movePending, setMovePending] = useState(false);

    function applyRoomState(nextRoomState: RoomState) {
        setRoomState(nextRoomState);
        setActiveRoomCode(nextRoomState.roomCode);
        setRoomError(null);
        setMovePending(false);
        setStatusMessage(getRoomStatusMessage(nextRoomState, user?.username));
    }

    function disconnectSocket() {
        if (!socketRef.current) return;

        manualDisconnectRef.current = true;
        socketRef.current.close();
        socketRef.current = null;
    }

    function connectToRoom(roomCode: string) {
        disconnectSocket();
        manualDisconnectRef.current = false;
        setRoomPhase("connecting");
        setStatusMessage(`Connecting to room ${roomCode}...`);
        setRoomError(null);

        const socket = new WebSocket(buildGameSocketUrl(roomCode));
        socketRef.current = socket;
        let opened = false;

        socket.onopen = () => {
            if (socketRef.current !== socket) return;

            opened = true;
            setRoomPhase("connected");
            setStatusMessage("Connected.");
        };

        socket.onmessage = (event) => {
            if (socketRef.current !== socket) return;

            try {
                const payload = JSON.parse(event.data) as unknown;
                if (isRoomState(payload)) {
                    setRoomPhase("connected");
                    applyRoomState(payload);
                } else if (isRoomError(payload)) {
                    setMovePending(false);
                    setRoomError(payload.message);
                    setStatusMessage(payload.message);
                }
            } catch {
                setMovePending(false);
                setStatusMessage("Connected to room. Listening for game updates.");
            }
        };

        socket.onerror = () => {
            if (socketRef.current !== socket) return;

            setRoomPhase("error");
            setRoomError("The room connection ran into an error.");
            setMovePending(false);
            setStatusMessage("Room connection failed.");
        };

        socket.onclose = () => {
            if (socketRef.current === socket) {
                socketRef.current = null;
            } else {
                return;
            }

            if (manualDisconnectRef.current) {
                manualDisconnectRef.current = false;
                return;
            }

            setRoomPhase("error");
            setRoomError(
                opened
                    ? "The room connection closed. Rejoin to continue playing."
                    : "Could not connect to that room. Try another code or create a new one."
            );
            setMovePending(false);
            setStatusMessage(opened ? "Connection lost." : "Room unavailable.");
        };
    }

    async function handleJoinRoom(event: React.SubmitEvent<HTMLFormElement>) {
        event.preventDefault();
        const nextCode = normalizeRoomCode(roomInput);

        if (!nextCode) {
            setRoomPhase("error");
            setRoomError("Enter a room code before joining.");
            return;
        }

        try {
            setRoomPhase("connecting");
            setRoomError(null);
            setStatusMessage(`Joining room ${nextCode}...`);

            const response = await joinRoom(nextCode);
            applyRoomState(response);
            setRoomInput(response.roomCode);
            connectToRoom(response.roomCode);
        } catch (error) {
            setActiveRoomCode(null);
            setRoomPhase("error");
            setRoomError(getApiErrorMessage(error, "Could not join that room."));
            setRoomState(null);
            setMovePending(false);
            setStatusMessage("Room join failed.");
        }
    }

    async function handleCreateRoom() {
        const preferredCode = normalizeRoomCode(roomInput);

        try {
            setRoomPhase("creating");
            setRoomError(null);
            setStatusMessage("Creating your private room...");

            const response = await createRoom({code: preferredCode || undefined});
            applyRoomState(response);
            setRoomInput(response.roomCode);
            connectToRoom(response.roomCode);
        } catch {
            setRoomPhase("error");
            setRoomError("Could not create a room right now. Try another code or retry in a moment.");
            setMovePending(false);
            setStatusMessage("Room creation failed.");
        }
    }

    function handleBoardColumnSelect(column: number) {
        const socket = socketRef.current;
        const playerSymbol = getCurrentUserSymbol(roomState, user?.username);

        if (!roomState || !playerSymbol) {
            setStatusMessage("Join the room as a player before making a move.");
            return;
        }

        if (roomState.currentPlayer.symbol !== playerSymbol) {
            setStatusMessage(getTurnMessage(roomState, user?.username));
            return;
        }

        if (!socket || socket.readyState !== WebSocket.OPEN) {
            setRoomError("The room socket is not connected.");
            setStatusMessage("Reconnect before making a move.");
            return;
        }

        setMovePending(true);
        setStatusMessage(`Move sent for column ${column + 1}. Waiting for server.`);
        socket.send(JSON.stringify({
            type: "player_move",
            player: {
                username: user?.username ?? null,
                symbol: playerSymbol,
            },
            column,
        }));
    }

    async function handleLeaveRoom() {
        const roomCode = activeRoomCode;

        try {
            if (roomCode) {
                await leaveRoom(roomCode);
            }
        } finally {
            disconnectSocket();
            setActiveRoomCode(null);
            setRoomState(null);
            setRoomPhase("idle");
            setRoomError(null);
            setMovePending(false);
            setStatusMessage("No room joined yet.");
        }
    }

    useEffect(() => {
        return () => {
            disconnectSocket();
        };
    }, []);

    const isInRoom = !!activeRoomCode;
    const isBusy = roomPhase === "creating" || roomPhase === "connecting";
    const playerSymbol = getCurrentUserSymbol(roomState, user?.username);
    const isCurrentTurn = !!playerSymbol && roomState?.currentPlayer.symbol === playerSymbol;
    const canSendMove = isInRoom && roomPhase === "connected" && roomState?.status === "ready" && isCurrentTurn && !movePending;
    const roomStatusLabel =
        movePending
            ? "Move Sent"
            : roomPhase === "connected" && roomState?.status === "ready"
                ? isCurrentTurn ? "Your Move" : "Opponent Turn"
                : roomPhase === "connected"
            ? "Room Live"
            : roomPhase === "connecting"
                ? "Connecting"
                : roomPhase === "creating"
                    ? "Creating"
                    : roomPhase === "error"
                        ? "Reconnect Needed"
                        : "Lobby";

    const heading = buildRoomHeading(roomState, user?.username);
    const boardCaption = roomState ? getRoomStatusMessage(roomState, user?.username) : undefined;

    const description = isInRoom
        ? "Share the room code, keep this board open, and the same screen becomes your live match UI once both players connect."
        : "Create a fresh game room or enter an existing code to join a private head-to-head match.";

    return (
        <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.18),transparent_28%),linear-gradient(180deg,#0f172a_0%,#020617_100%)] text-white">
            <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-8 lg:px-10">
                <header className="flex items-center justify-between gap-4">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-200/70">
                            Connect4 Online
                        </p>
                        <p className="mt-2 text-sm text-slate-300">
                            Signed in as <span className="font-semibold text-white">{user?.username ?? "Player"}</span>
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => void logout()}
                        className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:border-cyan-300/30 hover:bg-white/10"
                    >
                        Sign out
                    </button>
                </header>

                <main className="flex flex-1 items-center py-10">
                    <div className="grid w-full items-center gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(420px,1.05fr)]">
                        <section className="max-w-2xl">
                            <div className="inline-flex rounded-full border border-cyan-300/15 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-50">
                                {isInRoom ? `Room ${activeRoomCode}` : "Lobby"}
                            </div>

                            <h1 className="mt-6 max-w-xl text-4xl font-black tracking-tight text-white sm:text-5xl">
                                {heading}
                            </h1>
                            <p className="mt-4 max-w-xl text-lg leading-8 text-slate-300">
                                {description}
                            </p>

                            <div className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-slate-950/25 backdrop-blur">
                                <form className="space-y-5" onSubmit={handleJoinRoom}>
                                    <FormInput
                                        type="text"
                                        name="roomCode"
                                        label="Room code"
                                        value={roomInput}
                                        placeholder="Enter private room code"
                                        required={true}
                                        onChange={(event) => {
                                            setRoomInput(event.target.value.toUpperCase());
                                            setRoomError(null);
                                            if (roomPhase === "error") {
                                                setRoomPhase("idle");
                                                setStatusMessage("No room joined yet.");
                                            }
                                        }}
                                        valid={!roomError}
                                        validMessage={roomError ? [roomError] : undefined}
                                    />

                                    <div className="grid gap-3 sm:grid-cols-2">
                                        <MainButton disabled={isBusy}>
                                            {roomPhase === "connecting" ? "Joining room..." : "Join room"}
                                        </MainButton>
                                        <button
                                            type="button"
                                            disabled={isBusy}
                                            onClick={() => void handleCreateRoom()}
                                            className="rounded-md border border-cyan-300/25 bg-cyan-300/10 px-3 py-1.5 text-sm/6 font-semibold text-cyan-50 transition hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:border-cyan-300/10 disabled:bg-cyan-300/5 disabled:text-cyan-100/50"
                                        >
                                            {roomPhase === "creating" ? "Creating room..." : "Create room"}
                                        </button>
                                    </div>
                                </form>

                                <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-300">
                                    <span className="rounded-full border border-white/10 bg-slate-950/40 px-3 py-1">
                                        Status: {statusMessage}
                                    </span>
                                    {isInRoom && (
                                        <button
                                            type="button"
                                            onClick={() => void handleLeaveRoom()}
                                            className="rounded-full border border-white/10 px-3 py-1 text-slate-200 transition hover:border-cyan-300/30 hover:text-white"
                                        >
                                            Leave room
                                        </button>
                                    )}
                                </div>
                            </div>
                        </section>

                        <section>
                            <Connect4Board
                                active={isInRoom}
                                statusLabel={roomStatusLabel}
                                board={roomState?.board}
                                boardCaption={boardCaption}
                                canMove={canSendMove}
                                currentPlayerSymbol={roomState?.currentPlayer.symbol}
                                playerSymbol={playerSymbol}
                                movePending={movePending}
                                onColumnSelect={handleBoardColumnSelect}
                            />
                        </section>
                    </div>
                </main>
            </div>
        </div>
    );
}
