
import React, {useEffect, useRef, useState} from "react";
import Connect4Board from "../components/Connect4Board.tsx";
import FormInput from "../components/FormInput.tsx";
import MainButton from "../components/MainButton.tsx";
import SecondaryButton from "../components/SecondaryButton.tsx";
import {useAuth} from "../auth/useAuth.ts";
import {createRoom, joinRoom, leaveRoom, resetRoom, startBotGame, type PlayerSymbol, type RoomErrorResponse, type RoomState} from "../api/game.ts";
import {api} from "../api/client.ts";
import axios from "axios";

type RoomPhase = "idle" | "creating" | "connecting" | "connected" | "error";

type RoomAction = {
    label: string;
    disabled: boolean;
    onClick: () => void;
};

/**
 * Normalize user-entered room codes before they reach the API.
 *
 * @param value - Raw room-code input from the form.
 * @returns Uppercase code without whitespace.
 */
function normalizeRoomCode(value: string) {
    return value.trim().replace(/\s+/g, "").toUpperCase();
}

/**
 * Build the websocket URL that matches the configured REST API origin.
 *
 * @param roomCode - Normalized room code to connect to.
 * @returns Absolute ws:// or wss:// URL with the current access token query parameter.
 */
function buildGameSocketUrl(roomCode: string) {
    const apiBaseUrl = api.defaults.baseURL ?? "http://localhost:8000/api/";
    const backendUrl = new URL(apiBaseUrl);
    const protocol = backendUrl.protocol === "https:" ? "wss:" : "ws:";
    const token = localStorage.getItem("access_token");
    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : "";

    return `${protocol}//${backendUrl.host}/ws/game/${roomCode}/${tokenQuery}`;
}

/**
 * Extract a useful message from an unknown API error.
 *
 * @param error - Error thrown by an API call.
 * @param fallback - Message to use when the error does not match the expected shape.
 * @returns User-facing error message.
 */
function getApiErrorMessage(error: unknown, fallback: string) {
    if (axios.isAxiosError<{message?: string}>(error)) {
        return error.response?.data?.message ?? fallback;
    }

    return fallback;
}

/**
 * Narrow an unknown websocket payload to a room-state event.
 *
 * @param payload - Parsed JSON payload from the websocket.
 * @returns True when the payload has the minimum RoomState fields.
 */
function isRoomState(payload: unknown): payload is RoomState {
    if (!payload || typeof payload !== "object") return false;

    const candidate = payload as Partial<RoomState>;
    return typeof candidate.roomCode === "string" && typeof candidate.status === "string";
}

/**
 * Narrow an unknown websocket payload to a room-error event.
 *
 * @param payload - Parsed JSON payload from the websocket.
 * @returns True when the payload is a RoomErrorResponse.
 */
function isRoomError(payload: unknown): payload is RoomErrorResponse {
    if (!payload || typeof payload !== "object") return false;

    const candidate = payload as {type?: unknown; message?: unknown};
    return candidate.type === "room_error" && typeof candidate.message === "string";
}

/**
 * Build the headline describing the current matchup.
 *
 * @param roomState - Current room state or null when no room is joined.
 * @param fallbackUsername - Signed-in username used before the first room echo arrives.
 * @returns Heading text for the room panel.
 */
function buildRoomHeading(roomState: RoomState | null, fallbackUsername?: string) {
    if (!roomState) return "Private Connect 4";

    const player1 = roomState.player1 ?? "Waiting...";
    const player2 = roomState.player2 ?? "Waiting...";

    if (!roomState.player1 && !roomState.player2 && fallbackUsername) {
        return `${fallbackUsername} vs Waiting...`;
    }

    return `${player1} vs ${player2}`;
}

/**
 * Resolve the signed-in user's board symbol in a room.
 *
 * @param roomState - Current room state or null.
 * @param username - Signed-in username.
 * @returns Player symbol for this user, or null when they are not a participant.
 */
function getCurrentUserSymbol(roomState: RoomState | null, username?: string): PlayerSymbol | null {
    if (!roomState || !username) return null;

    if (roomState.player1 === username) return 1;
    if (roomState.player2 === username) return 2;
    return null;
}

/**
 * Describe whose turn it is or how the game ended.
 *
 * @param roomState - Current room state.
 * @param username - Signed-in username for personalized messages.
 * @returns Short status text for the board and room controls.
 */
function getTurnMessage(roomState: RoomState, username?: string) {
    if (roomState.status === "finished") {
        if (roomState.gameResult?.isDraw) {
            return "Game over. Draw.";
        }

        if (roomState.gameResult?.winner?.username === username) {
            return "Game over. You won.";
        }

        return `Game over. ${roomState.gameResult?.winner?.username ?? "Opponent"} won.`;
    }

    if (roomState.status !== "ready") {
        if (roomState.isBotGame) {
            return "Starting bot game.";
        }

        return "Waiting for another player.";
    }

    if (roomState.currentPlayer.username === username) {
        return "Your move.";
    }

    return `${roomState.currentPlayer.username ?? "Opponent"}'s move.`;
}

/**
 * Combine transient event details with the current turn message.
 *
 * @param roomState - Current room state including optional event context.
 * @param username - Signed-in username for personalized messages.
 * @returns User-facing room status text.
 */
function getRoomStatusMessage(roomState: RoomState, username?: string) {
    const turnMessage = getTurnMessage(roomState, username);

    if (roomState.type === "game_over") {
        return roomState.message ? `${roomState.message} ${turnMessage}` : turnMessage;
    }

    if (roomState.type === "player_move" && roomState.lastMove) {
        const playerName = roomState.lastMove.player.username ?? "A player";
        return `${playerName} played column ${roomState.lastMove.column + 1}. ${turnMessage}`;
    }

    return turnMessage;
}

/**
 * Main authenticated game room screen.
 *
 * @returns The lobby, room controls, and interactive Connect 4 board.
 */
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

    /**
     * Apply the authoritative room state returned by HTTP or websocket.
     *
     * @param nextRoomState - Server-confirmed room state.
     * @returns Nothing after updating local UI state.
     */
    function applyRoomState(nextRoomState: RoomState) {
        setRoomState(nextRoomState);
        setActiveRoomCode(nextRoomState.roomCode);
        setRoomError(null);
        setMovePending(false);
        setStatusMessage(getRoomStatusMessage(nextRoomState, user?.username));
    }

    /**
     * Close the current websocket while suppressing reconnect-style error UI.
     *
     * @returns Nothing.
     */
    function disconnectSocket() {
        if (!socketRef.current) return;

        manualDisconnectRef.current = true;
        socketRef.current.close();
        socketRef.current = null;
    }

    /**
     * Open a websocket connection for the selected room.
     *
     * @param roomCode - Normalized room code returned by the API.
     * @returns Nothing; websocket callbacks update React state over time.
     */
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

    /**
     * Join a room or leave the current one when already connected.
     *
     * @param event - Form submit event from the room-code form.
     * @returns Nothing after the request finishes.
     */
    async function handleJoinRoom(event: React.SubmitEvent<HTMLFormElement>) {
        event.preventDefault();

        if (activeRoomCode) {
            await handleLeaveRoom();
            return;
        }

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

    /**
     * Convert the active room into a bot game.
     *
     * @returns Nothing after the server accepts or rejects the request.
     */
    async function handleStartBotGame() {
        const roomCode = activeRoomCode;

        if (!roomCode) {
            setRoomError("Join or create a room before starting a bot game.");
            return;
        }

        try {
            setRoomPhase("connecting");
            setRoomError(null);
            setStatusMessage("Starting bot game...");

            const response = await startBotGame(roomCode);
            applyRoomState(response);
            setRoomInput(response.roomCode);
            setRoomPhase("connected");
        } catch (error) {
            setRoomPhase("connected");
            setRoomError(getApiErrorMessage(error, "Could not start a bot game in this room."));
            setMovePending(false);
            setStatusMessage("Bot game could not start.");
        }
    }

    /**
     * Create a new room using the optional preferred code.
     *
     * @returns Nothing after creating the room or displaying an error.
     */
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

    /**
     * Reset a finished room for another round.
     *
     * @returns Nothing after the reset request completes.
     */
    async function handleResetRoom() {
        const roomCode = activeRoomCode;

        if (!roomCode) {
            setRoomError("Join a room before resetting the game.");
            return;
        }

        try {
            setRoomPhase("connecting");
            setRoomError(null);
            setStatusMessage("Resetting game...");

            const response = await resetRoom(roomCode);
            applyRoomState(response);
            setRoomInput(response.roomCode);
            setRoomPhase("connected");
        } catch (error) {
            setRoomPhase("connected");
            setRoomError(getApiErrorMessage(error, "Could not reset this game."));
            setMovePending(false);
            setStatusMessage("Game reset failed.");
        }
    }

    /**
     * Submit a column choice over the websocket.
     *
     * @param column - Zero-based column index selected on the board.
     * @returns Nothing after sending the move or updating validation feedback.
     */
    function handleBoardColumnSelect(column: number) {
        const socket = socketRef.current;
        const playerSymbol = getCurrentUserSymbol(roomState, user?.username);

        if (!roomState || !playerSymbol) {
            setStatusMessage("Join the room as a player before making a move.");
            return;
        }

        if (roomState.currentPlayer.symbol !== playerSymbol) {
            // Trust the server turn state so local clicks cannot race ahead of broadcasts.
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

    /**
     * Leave the active room and reset all local room state.
     *
     * @returns Nothing after cleanup, even if the leave request fails.
     */
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
    const canStartBotGame =
        isInRoom &&
        roomPhase === "connected" &&
        roomState?.status === "waiting" &&
        !roomState.player2 &&
        !roomState.isBotGame;
    const canResetGame = isInRoom && roomPhase === "connected" && roomState?.status === "finished";
    const roomStatusLabel =
        movePending
            ? "Move Sent"
            : roomState?.status === "finished"
                ? "Game Over"
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
        ? roomState?.status === "finished"
            ? "The round is finished. Reset the game to play another round in this room."
            : roomState?.isBotGame
            ? "You are playing against the bot. This room is locked and cannot be joined by other players."
            : "Share the room code, keep this board open, or start a bot game before another player joins."
        : "Create a fresh game room or enter an existing code to join a private head-to-head match.";
    const secondaryAction: RoomAction = (() => {
        if (!isInRoom) {
            return {
                label: roomPhase === "creating" ? "Creating room..." : "Create room",
                disabled: isBusy,
                onClick: () => void handleCreateRoom(),
            };
        }

        if (roomState?.status === "finished") {
            return {
                label: roomPhase === "connecting" ? "Resetting..." : "Reset game",
                disabled: isBusy || !canResetGame,
                onClick: () => void handleResetRoom(),
            };
        }

        if (roomState?.player2) {
            return {
                label: "Reset game",
                disabled: true,
                onClick: () => undefined,
            };
        }

        if (roomState?.isBotGame) {
            return {
                label: "Playing bot",
                disabled: true,
                onClick: () => undefined,
            };
        }

        return {
            label: roomPhase === "connecting" ? "Starting bot..." : "Play with Bot",
            disabled: isBusy || !canStartBotGame,
            onClick: () => void handleStartBotGame(),
        };
    })();

    return (
        <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.18),transparent_28%),linear-gradient(180deg,#0f172a_0%,#020617_100%)] text-white">
            <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 sm:px-6 sm:py-6 lg:px-10 lg:py-8">
                <header className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200/70 sm:tracking-[0.35em]">
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

                <main className="flex flex-1 items-start py-4 sm:py-6 lg:items-center lg:py-10">
                    <div className="grid w-full items-center gap-4 sm:gap-6 lg:grid-cols-[minmax(320px,0.85fr)_minmax(430px,1.15fr)] lg:gap-10">
                        <section className="order-2 w-full max-w-2xl lg:order-1 lg:max-w-none">
                            <div className="hidden lg:block">
                                <div className="inline-flex rounded-full border border-cyan-300/15 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-50">
                                    {isInRoom ? `Room ${activeRoomCode}` : "Lobby"}
                                </div>

                                <h1 className="mt-6 max-w-xl text-5xl font-black tracking-tight text-white">
                                    {heading}
                                </h1>
                                <p className="mt-4 max-w-xl text-lg leading-8 text-slate-300">
                                    {description}
                                </p>
                            </div>

                            <div className="rounded-lg border border-white/10 bg-white/5 p-4 shadow-2xl shadow-slate-950/25 backdrop-blur sm:p-5 lg:mt-8 lg:p-6">
                                <form className="space-y-4 sm:space-y-5" onSubmit={handleJoinRoom}>
                                    <FormInput
                                        type="text"
                                        name="roomCode"
                                        label="Room code"
                                        value={roomInput}
                                        placeholder="Enter private room code"
                                        required={!isInRoom}
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
                                            {isInRoom ? "Leave room" : roomPhase === "connecting" ? "Joining room..." : "Join room"}
                                        </MainButton>
                                        <SecondaryButton
                                            disabled={secondaryAction.disabled}
                                            onClick={secondaryAction.onClick}
                                        >
                                            {secondaryAction.label}
                                        </SecondaryButton>
                                    </div>
                                </form>

                                <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-300">
                                    <span className="rounded-full border border-white/10 bg-slate-950/40 px-3 py-1">
                                        Status: {statusMessage}
                                    </span>
                                    {roomState?.isBotGame && (
                                        <span className="rounded-full border border-yellow-200/20 bg-yellow-300/10 px-3 py-1 text-yellow-50">
                                            Closed to joins
                                        </span>
                                    )}
                                </div>
                            </div>
                        </section>

                        <section className="order-1 w-full min-w-0 lg:order-2">
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
