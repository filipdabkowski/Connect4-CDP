
import React, {useEffect, useRef, useState} from "react";
import Connect4Board from "../components/Connect4Board.tsx";
import FormInput from "../components/FormInput.tsx";
import MainButton from "../components/MainButton.tsx";
import {useAuth} from "../auth/useAuth.ts";
import {createRoom} from "../api/game.ts";
import {api} from "../api/client.ts";

type RoomPhase = "idle" | "creating" | "connecting" | "connected" | "error";

function normalizeRoomCode(value: string) {
    return value.trim().replace(/\s+/g, "").toUpperCase();
}

function buildGameSocketUrl(roomCode: string) {
    const apiBaseUrl = api.defaults.baseURL ?? "http://localhost:8000/api/";
    const backendUrl = new URL(apiBaseUrl);
    const protocol = backendUrl.protocol === "https:" ? "wss:" : "ws:";

    return `${protocol}//${backendUrl.host}/ws/game/${roomCode}/`;
}

export default function HomePage() {
    const {user, logout} = useAuth();
    const socketRef = useRef<WebSocket | null>(null);
    const manualDisconnectRef = useRef(false);

    const [roomInput, setRoomInput] = useState("");
    const [activeRoomCode, setActiveRoomCode] = useState<string | null>(null);
    const [roomPhase, setRoomPhase] = useState<RoomPhase>("idle");
    const [roomError, setRoomError] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState("No room joined yet.");

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
            setStatusMessage("Connected. Waiting for the second player to join the room.");
        };

        socket.onmessage = (event) => {
            if (socketRef.current !== socket) return;

            try {
                const payload = JSON.parse(event.data) as {type?: string};
                if (payload.type === "room_state") {
                    setRoomPhase("connected");
                    setStatusMessage("Room synchronized. Your private match is ready.");
                }
            } catch {
                setStatusMessage("Connected to room. Listening for game updates.");
            }
        };

        socket.onerror = () => {
            if (socketRef.current !== socket) return;

            setRoomPhase("error");
            setRoomError("The room connection ran into an error.");
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

        setActiveRoomCode(nextCode);
        setRoomInput(nextCode);
        connectToRoom(nextCode);
    }

    async function handleCreateRoom() {
        const preferredCode = normalizeRoomCode(roomInput);

        try {
            setRoomPhase("creating");
            setRoomError(null);
            setStatusMessage("Creating your private room...");

            const response = await createRoom({code: preferredCode || undefined});
            setActiveRoomCode(response.roomCode);
            setRoomInput(response.roomCode);
            connectToRoom(response.roomCode);
        } catch {
            setRoomPhase("error");
            setRoomError("Could not create a room right now. Try another code or retry in a moment.");
            setStatusMessage("Room creation failed.");
        }
    }

    function handleLeaveRoom() {
        disconnectSocket();
        setActiveRoomCode(null);
        setRoomPhase("idle");
        setRoomError(null);
        setStatusMessage("No room joined yet.");
    }

    useEffect(() => {
        return () => {
            disconnectSocket();
        };
    }, []);

    const isInRoom = !!activeRoomCode;
    const isBusy = roomPhase === "creating" || roomPhase === "connecting";
    const roomStatusLabel =
        roomPhase === "connected"
            ? "Room Live"
            : roomPhase === "connecting"
                ? "Connecting"
                : roomPhase === "creating"
                    ? "Creating"
                    : roomPhase === "error"
                        ? "Reconnect Needed"
                        : "Lobby";

    const heading = isInRoom
        ? `${user?.username ?? "Player 1"} vs Waiting for player 2`
        : "Private Connect 4, one room at a time";

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
                                            onClick={handleLeaveRoom}
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
                            />
                        </section>
                    </div>
                </main>
            </div>
        </div>
    );
}
