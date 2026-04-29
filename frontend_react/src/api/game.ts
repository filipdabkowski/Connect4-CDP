import { api } from "./client";

export type CreateRoomPayload = {
    code?: string;
};

export type CreateRoomResponse = {
    roomCode: string;
    symbol: string;
};

export async function createRoom(payload: CreateRoomPayload): Promise<CreateRoomResponse> {
    const body = payload.code ? { code: payload.code } : {};
    const response = await api.post<CreateRoomResponse>("/game/rooms/create/", body);
    return response.data;
}
