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
    type: "room_state" | "room_joined" | "player_move" | "game_over";
    roomCode: string;
    status: RoomStatus;
    player1: string | null;
    player2: string | null;
    board: BoardState;
    currentPlayer: RoomPlayer;
    gameResult: GameResult | null;
    lastMove?: LastMove;
    message?: string;
};

export type CreateRoomResponse = RoomState;
export type JoinRoomResponse = CreateRoomResponse;
export type LeaveRoomResponse = RoomState;

export async function createRoom(payload: CreateRoomPayload): Promise<CreateRoomResponse> {
    const body = payload.code ? { code: payload.code } : {};
    const response = await api.post<CreateRoomResponse>("/game/rooms/create/", body);
    return response.data;
}

export async function joinRoom(roomCode: string): Promise<JoinRoomResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await api.post<JoinRoomResponse>(
        `/game/rooms/${encodeURIComponent(code)}/join/`,
        { code },
    );
    return response.data;
}

export async function leaveRoom(roomCode: string): Promise<LeaveRoomResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await api.post<LeaveRoomResponse>(
        `/game/rooms/${encodeURIComponent(code)}/leave/`,
        { code },
    );
    return response.data;
}
