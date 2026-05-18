import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import {ROUTES} from "../ROUTES.ts";

/**
 * Guard routes that require an authenticated user.
 *
 * @param children - Protected page content to render after authentication.
 * @returns The children for signed-in users, otherwise a redirect to login.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuth } = useAuth();

  if (!isAuth) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <>{children}</>;
}
