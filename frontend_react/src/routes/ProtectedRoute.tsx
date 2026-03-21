import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import {ROUTES} from "../ROUTES.ts";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuth } = useAuth();

  if (!isAuth) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <>{children}</>;
}
