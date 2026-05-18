import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import {ROUTES} from "../ROUTES.ts";

/**
 * Guard routes that should only be visible before sign-in.
 *
 * @param children - Public page content such as login or registration.
 * @returns The children for guests, otherwise a redirect to the home page.
 */
export function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuth } = useAuth();

  if (isAuth) {
    return <Navigate to={ROUTES.HOME} replace />;
  }

  return <>{children}</>;
}
