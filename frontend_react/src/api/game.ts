import { api } from "./client";

export type CreateRoomPayload = {
    code?: string;
};

export type RoomStatus = "waiting" | "ready" | "finished";
export type BoardCell = 0 | 1 | 2;
export type BoardState = BoardCell[][];
export type PlayerSymbol = 1 | 2;
export type PlayerSlot = "player1" | "player2";

export type RoomPlayer = {
    symbol: PlayerSymbol;
    slot: PlayerSlot;
    username: string | null;
};

export type LastMove = {
    player: RoomPlayer;
    column: number;
};

export type GameResult = {
    winner: RoomPlayer | null;
    isDraw: boolean;
};

export type RoomErrorResponse = {
    type: "room_error";
    message: string;
};

export type RoomState = {
    type: "room_state" | "room_joined" | "room_reset" | "bot_game_started" | "player_move" | "game_over";
    roomCode: string;
    status: RoomStatus;
    player1: string | null;
    player2: string | null;
    board: BoardState;
    currentPlayer: RoomPlayer;
    isBotGame: boolean;
    gameResult: GameResult | null;
    lastMove?: LastMove;
    message?: string;
};

export type CreateRoomResponse = RoomState;
export type JoinRoomResponse = CreateRoomResponse;
export type LeaveRoomResponse = RoomState;
export type ResetRoomResponse = RoomState;
export type StartBotGameResponse = RoomState;

/**
 * Create a room for the authenticated player.
 *
 * @param payload - Optional preferred room code.
 * @returns The newly created room state.
 */
export async function createRoom(payload: CreateRoomPayload): Promise<CreateRoomResponse> {
    const body = payload.code ? { code: payload.code } : {};
    const response = await api.post<CreateRoomResponse>("/game/rooms/create/", body);
    return response.data;
}

/**
 * Join a room by code.
 *
 * @param roomCode - Human-entered room code; whitespace/case are normalized before sending.
 * @returns The joined room state.
 */
export async function joinRoom(roomCode: string): Promise<JoinRoomResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await api.post<JoinRoomResponse>(
        `/game/rooms/${encodeURIComponent(code)}/join/`,
        { code },
    );
    return response.data;
}

/**
 * Leave the active room.
 *
 * @param roomCode - Room code to leave; whitespace/case are normalized before sending.
 * @returns The room state after this player leaves.
 */
export async function leaveRoom(roomCode: string): Promise<LeaveRoomResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await api.post<LeaveRoomResponse>(
        `/game/rooms/${encodeURIComponent(code)}/leave/`,
        { code },
    );
    return response.data;
}

/**
 * Reset a finished room for another round.
 *
 * @param roomCode - Room code to reset; whitespace/case are normalized before sending.
 * @returns The reset room state.
 */
export async function resetRoom(roomCode: string): Promise<ResetRoomResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await api.post<ResetRoomResponse>(
        `/game/rooms/${encodeURIComponent(code)}/reset/`,
        { code },
    );
    return response.data;
}

/**
 * Convert a waiting room into a bot game.
 *
 * @param roomCode - Room code to update; whitespace/case are normalized before sending.
 * @returns The bot-enabled room state.
 */
export async function startBotGame(roomCode: string): Promise<StartBotGameResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await api.post<StartBotGameResponse>(
        `/game/rooms/${encodeURIComponent(code)}/bot/start/`,
        { code },
    );
    return response.data;
}
